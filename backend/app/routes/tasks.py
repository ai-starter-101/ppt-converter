"""任务相关 API 路由"""
import uuid
import json
import asyncio
from pathlib import Path
from typing import List, Optional, Callable
from fastapi import APIRouter, HTTPException, UploadFile, File, Depends, Query
from fastapi.responses import StreamingResponse
from sqlmodel import Session, select
from app.database import get_session
from app.models import Task, slides_to_json, parse_slides_json
from app.services import (
    extract_text_from_ppt,
    get_ppt_info,
    generate_script_per_page,
    generate_audio,
    generate_audio_per_page,
    get_audio_duration,
    generate_slide_screenshots_async
)
from app.config import settings
import aiofiles

router = APIRouter(prefix="/api/tasks", tags=["任务管理"])

# 存储进度回调 {task_id: (queue, cancel_event)}
progress_stores: dict = {}


# 添加 OPTIONS 路由处理 CORS 预检请求
@router.options("")
async def tasks_options():
    """处理任务相关请求的 CORS 预检"""
    from fastapi.responses import Response
    return Response(
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
            "Access-Control-Allow-Headers": "*",
        }
    )


@router.options("/{task_id}/audio/{page_num}")
async def audio_options():
    """处理音频请求的 CORS 预检"""
    from fastapi.responses import Response
    return Response(
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, OPTIONS",
            "Access-Control-Allow-Headers": "*",
        }
    )


@router.post("")
async def create_task(session: Session = Depends(get_session)) -> dict:
    """创建新任务"""
    task = Task(
        id=str(uuid.uuid4()),
        filename="",
        file_path="",
        status="pending"
    )
    session.add(task)
    session.commit()
    session.refresh(task)
    return {"id": task.id, "status": task.status}


@router.get("")
async def list_tasks(session: Session = Depends(get_session)) -> List[dict]:
    """获取任务列表"""
    tasks = session.exec(select(Task).order_by(Task.created_at.desc())).all()
    return [task.model_dump() for task in tasks]


@router.get("/{task_id}")
async def get_task(task_id: str, session: Session = Depends(get_session)) -> dict:
    """获取任务详情"""
    task = session.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    # 自动修复状态：如果音频已生成但状态不是 audio_ready，则修复
    if task.status == "script_ready" and task.slides_audio:
        try:
            # 解析音频数据
            if isinstance(task.slides_audio, str):
                audios = parse_slides_json(task.slides_audio)
            else:
                audios = task.slides_audio
            # 检查是否有有效的音频
            valid_audios = [a for a in audios if a.get("audio_path")]
            if len(valid_audios) >= task.slide_count:
                task.status = "audio_ready"
                session.commit()
                print(f"自动修复任务状态: {task_id} -> audio_ready")
        except Exception as e:
            print(f"自动修复状态失败: {e}")

    return task.model_dump()


@router.delete("/{task_id}")
async def delete_task(task_id: str, session: Session = Depends(get_session)) -> dict:
    """删除任务"""
    task = session.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    # 删除关联的文件
    try:
        # 删除 PPT 文件
        if task.file_path and Path(task.file_path).exists():
            Path(task.file_path).unlink()

        # 删除截图目录
        screenshot_dir = settings.static_dir / "screenshots" / task_id
        if screenshot_dir.exists():
            import shutil
            shutil.rmtree(screenshot_dir)

        # 删除音频目录
        audio_dir = settings.audio_dir / task_id
        if audio_dir.exists():
            import shutil
            shutil.rmtree(audio_dir)

        # 删除视频目录
        video_dir = settings.static_dir / "video" / task_id
        if video_dir.exists():
            import shutil
            shutil.rmtree(video_dir)

    except Exception as e:
        # 文件删除失败不影响任务删除
        print(f"警告: 删除文件失败: {e}")

    # 删除数据库记录
    session.delete(task)
    session.commit()

    return {"message": "任务已删除", "task_id": task_id}


@router.post("/batch-delete")
async def batch_delete_tasks(request: dict, session: Session = Depends(get_session)) -> dict:
    """批量删除任务"""
    task_ids: List[str] = request.get("task_ids", [])
    if not task_ids:
        raise HTTPException(status_code=400, detail="任务ID列表为空")

    # 获取要删除的任务
    tasks = session.exec(select(Task).where(Task.id.in_(task_ids))).all()

    deleted_ids = []
    failed_ids = []

    for task in tasks:
        task_id = task.id
        try:
            # 删除关联的文件
            try:
                # 删除 PPT 文件
                if task.file_path and Path(task.file_path).exists():
                    Path(task.file_path).unlink()

                # 删除截图目录
                screenshot_dir = settings.static_dir / "screenshots" / task_id
                if screenshot_dir.exists():
                    import shutil
                    shutil.rmtree(screenshot_dir)

                # 删除音频目录
                audio_dir = settings.audio_dir / task_id
                if audio_dir.exists():
                    import shutil
                    shutil.rmtree(audio_dir)

                # 删除视频目录
                video_dir = settings.static_dir / "video" / task_id
                if video_dir.exists():
                    import shutil
                    shutil.rmtree(video_dir)
            except Exception as e:
                print(f"警告: 删除任务 {task_id} 文件失败: {e}")

            # 删除数据库记录
            session.delete(task)
            deleted_ids.append(task_id)
        except Exception as e:
            print(f"警告: 删除任务 {task_id} 失败: {e}")
            failed_ids.append(task_id)

    session.commit()

    return {
        "message": f"成功删除 {len(deleted_ids)} 个任务",
        "deleted_count": len(deleted_ids),
        "deleted_ids": deleted_ids,
        "failed_ids": failed_ids
    }


@router.post("/{task_id}/upload")
async def upload_ppt(
    task_id: str,
    file: UploadFile = File(...),
    session: Session = Depends(get_session)
) -> dict:
    """上传 PPT 文件"""
    task = session.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    # 验证文件类型
    if not file.filename or not file.filename.endswith('.pptx'):
        raise HTTPException(status_code=400, detail="只支持 .pptx 格式")

    # 生成唯一文件名
    file_ext = Path(file.filename).suffix
    unique_filename = f"{task_id}{file_ext}"
    file_path = settings.upload_dir / unique_filename

    # 确保目录存在
    settings.upload_dir.mkdir(parents=True, exist_ok=True)

    # 保存文件
    async with aiofiles.open(file_path, 'wb') as f:
        content = await file.read()
        await f.write(content)

    # 验证文件并提取幻灯片内容
    try:
        ppt_info = get_ppt_info(str(file_path))
        slides_content = ppt_info["slides"]
    except Exception as e:
        file_path.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail=f"无效的 PPT 文件: {str(e)}")

    # 生成幻灯片截图
    try:
        screenshots = await generate_slide_screenshots_async(str(file_path), task_id)
    except Exception as e:
        # 截图生成失败不影响主流程，只记录警告
        print(f"警告: 生成截图失败: {e}")
        screenshots = []

    # 更新任务
    task.filename = file.filename
    task.file_path = str(file_path)
    task.status = "uploaded"
    task.slide_count = ppt_info["slide_count"]
    task.slides_content = slides_to_json(slides_content)
    task.slides_screenshots = slides_to_json(screenshots)
    session.commit()

    return {
        "id": task.id,
        "filename": task.filename,
        "status": task.status,
        "slide_count": task.slide_count,
        "slides": slides_content,
        "screenshots": screenshots
    }


@router.get("/{task_id}/slides")
async def get_slides(task_id: str, session: Session = Depends(get_session)) -> dict:
    """获取幻灯片内容"""
    task = session.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    if not task.slides_content:
        raise HTTPException(status_code=400, detail="请先上传 PPT 文件")

    slides = parse_slides_json(task.slides_content)
    scripts = parse_slides_json(task.slides_script)
    audios = parse_slides_json(task.slides_audio)
    screenshots = parse_slides_json(task.slides_screenshots)

    # 创建截图查找字典（优先使用数据库中的路径，如果文件不存在则查找其他可能）
    screenshots_dict = {}
    screenshot_dir = settings.static_dir / "screenshots" / task_id

    for s in screenshots:
        page_num = s["page_num"]
        saved_path = s.get("screenshot_path", "")

        # 检查保存的路径是否有效
        if saved_path:
            full_path = settings.static_dir / saved_path.lstrip("/static/")
            if full_path.exists():
                screenshots_dict[page_num] = saved_path
                continue

        # 如果数据库中的路径无效，查找目录中的其他可能文件
        if screenshot_dir.exists():
            # 尝试多种可能的文件名格式
            possible_names = [
                f"page_{page_num}.png",
                f"page_{page_num}.jpg",
                f"page_{page_num}.jpeg",
                f"{task_id}-{page_num:02d}.png",  # LibreOffice 格式
                f"幻灯片{page_num}.png",
                f"slide_{page_num}.png",
            ]
            for name in possible_names:
                alt_path = screenshot_dir / name
                if alt_path.exists():
                    screenshots_dict[page_num] = f"/static/screenshots/{task_id}/{name}"
                    break

    # 合并数据
    result = []
    for slide in slides:
        page_num = slide["page_num"]
        # 如果没有生成脚本，使用 PPT 内容作为默认脚本
        generated_script = next((s["script"] for s in scripts if s["page_num"] == page_num), "")
        script = generated_script if generated_script else slide["content"]
        audio = next((a for a in audios if a["page_num"] == page_num), None)

        result.append({
            "page_num": page_num,
            "content": slide["content"],
            "script": script,
            "audio": audio,
            "screenshot": screenshots_dict.get(page_num)
        })

    return {
        "task_id": task_id,
        "filename": task.filename,
        "slides": result
    }


@router.post("/{task_id}/scripts/generate")
async def generate_scripts(
    task_id: str,
    session: Session = Depends(get_session)
) -> dict:
    """按页生成所有脚本"""
    task = session.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    if task.status not in ["uploaded", "script_ready"]:
        raise HTTPException(status_code=400, detail="请先上传 PPT 文件")

    # 获取幻灯片内容
    slides = parse_slides_json(task.slides_content)
    if not slides:
        raise HTTPException(status_code=400, detail="幻灯片内容为空")

    # 按页生成脚本
    scripts = await generate_script_per_page(slides)

    # 保存脚本
    task.slides_script = slides_to_json(scripts)
    task.status = "script_ready"
    session.commit()

    return {
        "task_id": task_id,
        "scripts": scripts,
        "status": task.status
    }


@router.post("/{task_id}/scripts/{page_num}/generate")
async def generate_single_script(
    task_id: str,
    page_num: int,
    session: Session = Depends(get_session)
) -> dict:
    """生成单页脚本"""
    task = session.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    if task.status not in ["uploaded", "script_ready"]:
        raise HTTPException(status_code=400, detail="请先上传 PPT 文件")

    # 获取幻灯片内容
    slides = parse_slides_json(task.slides_content)
    slide = next((s for s in slides if s["page_num"] == page_num), None)

    if not slide:
        raise HTTPException(status_code=404, detail="幻灯片不存在")

    # 生成单页脚本
    scripts = await generate_script_per_page([slide])
    script = scripts[0] if scripts else {"page_num": page_num, "script": ""}

    # 保存脚本
    all_scripts = parse_slides_json(task.slides_script)
    updated = False
    for s in all_scripts:
        if s["page_num"] == page_num:
            s["script"] = script["script"]
            updated = True
            break

    if not updated:
        all_scripts.append({"page_num": page_num, "script": script["script"]})

    task.slides_script = slides_to_json(all_scripts)
    task.status = "script_ready"
    session.commit()

    return {
        "task_id": task_id,
        "page_num": page_num,
        "script": script["script"],
        "status": task.status
    }


@router.put("/{task_id}/scripts/{page_num}")
async def update_script(
    task_id: str,
    page_num: int,
    script_data: dict,
    session: Session = Depends(get_session)
) -> dict:
    """更新单页脚本"""
    task = session.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    scripts = parse_slides_json(task.slides_script)

    # 更新或添加脚本
    updated = False
    for s in scripts:
        if s["page_num"] == page_num:
            s["script"] = script_data.get("script", "")
            updated = True
            break

    if not updated:
        scripts.append({
            "page_num": page_num,
            "script": script_data.get("script", "")
        })

    task.slides_script = slides_to_json(scripts)
    task.status = "script_ready"
    session.commit()

    return {
        "task_id": task_id,
        "page_num": page_num,
        "script": script_data.get("script", ""),
        "status": task.status
    }


@router.post("/{task_id}/audio/{page_num}")
async def generate_audio_page(
    task_id: str,
    page_num: int,
    session: Session = Depends(get_session)
) -> dict:
    """生成单页音频"""
    task = session.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    if task.status not in ["uploaded", "script_ready"]:
        raise HTTPException(status_code=400, detail="请先生成脚本")

    # 获取脚本
    scripts = parse_slides_json(task.slides_script)
    script = next((s["script"] for s in scripts if s["page_num"] == page_num), "")

    if not script:
        raise HTTPException(status_code=400, detail=f"第 {page_num} 页脚本为空")

    # 生成音频
    audio_dir = settings.audio_dir / task_id
    audio_path = audio_dir / f"page_{page_num}.mp3"

    try:
        duration = await generate_audio(script, str(audio_path))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"生成音频失败: {str(e)}")

    # 更新音频信息
    audios = parse_slides_json(task.slides_audio)
    updated = False
    for a in audios:
        if a["page_num"] == page_num:
            a["audio_path"] = str(audio_path)
            a["duration"] = duration
            updated = True
            break

    if not updated:
        audios.append({
            "page_num": page_num,
            "audio_path": str(audio_path),
            "duration": duration
        })

    task.slides_audio = slides_to_json(audios)
    task.status = "audio_ready"
    session.commit()

    return {
        "task_id": task_id,
        "page_num": page_num,
        "audio_path": f"/static/audio/{task_id}/page_{page_num}.mp3",
        "duration": duration,
        "status": task.status
    }


@router.get("/{task_id}/audio/{page_num}")
async def get_audio_page(task_id: str, page_num: int, session: Session = Depends(get_session)):
    """获取单页音频文件流"""
    task = session.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    audio_path = settings.audio_dir / task_id / f"page_{page_num}.mp3"

    if not audio_path.exists():
        raise HTTPException(status_code=404, detail="音频文件不存在")

    from fastapi.responses import FileResponse
    response = FileResponse(
        path=str(audio_path),
        media_type="audio/mpeg",
        filename=f"{task_id}_page_{page_num}.mp3"
    )
    # 添加 CORS 头，允许跨域访问
    response.headers["Access-Control-Allow-Origin"] = "*"
    return response


@router.options("/{task_id}/audio/generate-all")
async def audio_generate_all_options():
    """处理批量音频生成请求的 CORS 预检"""
    from fastapi.responses import Response
    return Response(
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "POST, OPTIONS",
            "Access-Control-Allow-Headers": "*",
        }
    )


@router.post("/{task_id}/audio/generate-all")
async def generate_all_audio(
    task_id: str,
    session: Session = Depends(get_session)
) -> dict:
    """生成所有页面的音频"""
    task = session.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    if task.status not in ["uploaded", "script_ready"]:
        raise HTTPException(status_code=400, detail="请先上传 PPT 文件")

    scripts = parse_slides_json(task.slides_script)
    slides_content = parse_slides_json(task.slides_content)

    # 如果没有脚本，使用 PPT 内容作为默认脚本
    if not scripts:
        scripts = [{"page_num": s["page_num"], "script": s["content"]} for s in slides_content]
        # 保存生成的脚本到数据库
        task.slides_script = slides_to_json(scripts)
        session.commit()

    # 过滤有脚本的页面
    valid_scripts = [s for s in scripts if s.get("script", "").strip()]

    if not valid_scripts:
        raise HTTPException(status_code=400, detail="没有可生成音频的脚本")

    # 获取已有的音频信息，跳过已成功的页面
    existing_audios = parse_slides_json(task.slides_audio)

    # 按页生成音频
    audio_dir = settings.audio_dir / task_id
    audio_results = await generate_audio_per_page(valid_scripts, str(audio_dir), existing_audios=existing_audios)

    task.slides_audio = slides_to_json(audio_results)
    task.status = "audio_ready"
    session.commit()

    return {
        "task_id": task_id,
        "audios": audio_results,
        "status": task.status
    }


async def audio_generator_stream(task_id: str):
    """生成音频并流式输出进度 - 使用独立数据库连接"""
    from app.database import async_session

    # 使用独立数据库会话进行验证
    async with async_session() as session:
        task = await session.get(Task, task_id)
        if not task:
            yield json.dumps({"error": "任务不存在"})
            return

        if task.status not in ["uploaded", "script_ready"]:
            yield json.dumps({"error": "请先上传 PPT 文件"})
            return

        scripts = parse_slides_json(task.slides_script)
        slides_content = parse_slides_json(task.slides_content)

        # 如果没有脚本，使用 PPT 内容作为默认脚本
        if not scripts:
            scripts = [{"page_num": s["page_num"], "script": s["content"]} for s in slides_content]
            task.slides_script = slides_to_json(scripts)
            await session.commit()
            yield json.dumps({"type": "script_saved", "message": "已使用 PPT 内容作为默认脚本"})

        valid_scripts = [s for s in scripts if s.get("script", "").strip()]

        if not valid_scripts:
            yield json.dumps({"error": "没有可生成音频的脚本"})
            return

        # 获取已有的音频信息，跳过已成功的页面
        existing_audios = parse_slides_json(task.slides_audio)

    audio_dir = settings.audio_dir / task_id

    # 使用 asyncio.Queue 收集进度更新
    progress_queue: asyncio.Queue = asyncio.Queue()

    async def progress_callback(current: int, total: int, page_num: Optional[int]):
        """进度回调 - 发送到队列"""
        data = {
            "type": "progress",
            "current": current,
            "total": total,
            "percent": round(current / total * 100) if total > 0 else 100,
            "page_num": page_num
        }
        await progress_queue.put(data)

    # 在后台运行音频生成，同时读取队列发送进度
    async def run_generation():
        # 使用独立的 session 确保状态更新能被提交
        from app.database import async_session
        from sqlmodel import select

        try:
            async with async_session() as inner_session:
                # 重新查询任务确保是当前 session 的对象
                inner_task = await inner_session.get(Task, task_id)
                if not inner_task:
                    await progress_queue.put({"type": "error", "error": "任务不存在"})
                    return

                audio_results = await generate_audio_per_page(
                    valid_scripts, str(audio_dir), progress_callback, existing_audios
                )
                inner_task.slides_audio = slides_to_json(audio_results)
                inner_task.status = "audio_ready"
                await inner_session.commit()

                # 发送完成消息
                await progress_queue.put({"type": "complete", "status": "audio_ready"})
        except Exception as e:
            logger.error(f"音频生成任务失败: {e}")
            # 尝试更新任务状态为失败
            try:
                async with async_session() as error_session:
                    error_task = await error_session.get(Task, task_id)
                    if error_task and error_task.status != "audio_ready":
                        error_task.status = "script_ready"  # 回退到脚本状态
                        await error_session.commit()
            except Exception as update_error:
                logger.error(f"更新任务状态失败: {update_error}")
            await progress_queue.put({"type": "error", "error": f"音频生成失败: {str(e)}"})

    # 并发执行：生成音频 + 发送进度
    generation_task = asyncio.create_task(run_generation())

    # 从队列读取并发送进度（无超时限制）
    while True:
        try:
            data = await progress_queue.get()
            yield json.dumps(data)
            if data.get("type") == "complete":
                break
        except asyncio.CancelledError:
            break

    await generation_task


@router.get("/{task_id}/audio/generate-all/stream")
async def stream_audio_generation(task_id: str):
    """流式生成音频并返回进度"""
    async def event_generator():
        async for data in audio_generator_stream(task_id):
            yield f"data: {data}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
        }
    )


@router.post("/{task_id}/screenshots/upload")
async def upload_screenshots(
    task_id: str,
    files: List[UploadFile] = File(...),
    session: Session = Depends(get_session)
) -> dict:
    """
    上传幻灯片截图

    支持多种文件名格式：
    - page_1.png, page_2.png
    - 幻灯片1.jpeg, 幻灯片2.png
    - slide_1.png
    """
    task = session.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    # 确保截图目录存在
    screenshot_dir = settings.static_dir / "screenshots" / task_id
    screenshot_dir.mkdir(parents=True, exist_ok=True)

    uploaded = []

    for file in files:
        if not file.filename:
            continue

        filename = file.filename
        page_num = None

        # 尝试多种格式解析页码
        # 格式1: page_1.png, page_2.png
        if filename.startswith("page_"):
            try:
                page_num = int(filename.split('_')[1].split('.')[0])
            except (IndexError, ValueError):
                pass

        # 格式2: 幻灯片1.jpeg, 幻灯片2.png
        if page_num is None:
            import re
            match = re.search(r'幻灯片(\d+)', filename)
            if match:
                page_num = int(match.group(1))

        # 格式3: slide_1.png
        if page_num is None:
            match = re.search(r'slide_?(\d+)', filename, re.IGNORECASE)
            if match:
                page_num = int(match.group(1))

        if page_num is None:
            print(f"警告: 无法解析截图文件名 {filename} 的页码，跳过该文件")
            continue

        # 保存文件
        file_ext = Path(filename).suffix.lower()
        if not file_ext or file_ext not in ['.png', '.jpg', '.jpeg', '.gif']:
            file_ext = '.png'  # 默认使用 png

        save_name = f"page_{page_num}{file_ext}"
        file_path = screenshot_dir / save_name

        async with aiofiles.open(file_path, 'wb') as f:
            content = await file.read()
            await f.write(content)

        uploaded.append({
            "page_num": page_num,
            "screenshot_path": f"/static/screenshots/{task_id}/{save_name}"
        })

    if not uploaded:
        raise HTTPException(status_code=400, detail="没有成功上传任何截图")

    # 更新任务中的截图信息
    existing_screenshots = parse_slides_json(task.slides_screenshots) if task.slides_screenshots else []

    for new_screenshot in uploaded:
        updated = False
        for s in existing_screenshots:
            if s["page_num"] == new_screenshot["page_num"]:
                s["screenshot_path"] = new_screenshot["screenshot_path"]
                updated = True
                break
        if not updated:
            existing_screenshots.append(new_screenshot)

    task.slides_screenshots = slides_to_json(existing_screenshots)
    session.commit()

    return {
        "task_id": task_id,
        "screenshots": uploaded,
        "status": task.status
    }


@router.post("/{task_id}/scripts/upload")
async def upload_script(
    task_id: str,
    file: UploadFile = File(...),
    session: Session = Depends(get_session)
) -> dict:
    """
    上传脚本文件

    支持两种格式：
    1. 文本格式：按行分割，每行对应一页幻灯片的脚本
    2. JSONL 格式：每行一个 JSON 对象，格式如 {"page": 1, "title": "xxx", "script": "content"}
    """
    task = session.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    if not file.filename:
        raise HTTPException(status_code=400, detail="文件名不能为空")

    # 验证文件类型
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in ['.txt', '.md', '.text', '.jsonl']:
        raise HTTPException(status_code=400, detail="只支持 .txt、.md、.jsonl 格式的脚本文件")

    # 读取文件内容
    content = await file.read()
    try:
        text_content = content.decode('utf-8')
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="文件编码不支持，请使用 UTF-8 编码")

    # 获取幻灯片数量
    slides = parse_slides_json(task.slides_content)
    if not slides:
        raise HTTPException(status_code=400, detail="请先上传 PPT 文件")

    slide_count = len(slides)
    scripts = []

    # 尝试解析 JSON 数组格式或 JSONL 格式
    json_array_data = None
    is_jsonl = False

    # 首先尝试解析为 JSON 数组格式
    try:
        json_array_data = json.loads(text_content)
        if isinstance(json_array_data, list) and len(json_array_data) > 0:
            # 是 JSON 数组格式
            json_array_data = [obj for obj in json_array_data if "page" in obj or "page_num" in obj]
    except json.JSONDecodeError:
        json_array_data = None

    # 如果不是 JSON 数组格式，尝试 JSONL 格式
    if not json_array_data:
        try:
            lines = text_content.strip().split('\n')
            jsonl_data = []
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                obj = json.loads(line)
                if "script" in obj:
                    jsonl_data.append(obj)
            # 如果成功解析出有效数据，认为是 JSONL 格式
            if jsonl_data and all("page" in obj or "page_num" in obj for obj in jsonl_data):
                is_jsonl = True
                json_array_data = jsonl_data
        except json.JSONDecodeError:
            is_jsonl = False

    # 使用 JSON 数组数据（无论是 JSON 数组还是 JSONL 格式）
    if json_array_data:
        is_jsonl = True
        # JSON 数组或 JSONL 格式：按 page/page_num 字段匹配
        for i in range(slide_count):
            page_num = slides[i]["page_num"]
            # 查找对应的脚本
            script_obj = next(
                (obj for obj in json_array_data if obj.get("page") == page_num or obj.get("page_num") == page_num),
                None
            )
            script_content = script_obj.get("script", "") if script_obj else ""
            scripts.append({
                "page_num": page_num,
                "script": script_content
            })
    else:
        # 文本格式：按行分割，每行对应一页
        lines = text_content.split('\n')
        # 过滤空行
        non_empty_lines = [line.strip() for line in lines if line.strip()]

        # 为每页分配脚本
        for i in range(slide_count):
            page_num = slides[i]["page_num"]
            if i < len(non_empty_lines):
                script_content = non_empty_lines[i]
            else:
                script_content = ""

            scripts.append({
                "page_num": page_num,
                "script": script_content
            })

    # 保存到数据库
    task.slides_script = slides_to_json(scripts)
    task.status = "script_ready"
    session.commit()

    return {
        "task_id": task_id,
        "scripts": scripts,
        "slide_count": slide_count,
        "format": "jsonl" if is_jsonl else "text",
        "status": task.status
    }


@router.post("/{task_id}/video/synthesize")
async def synthesize_video(
    task_id: str,
    session: Session = Depends(get_session)
) -> dict:
    """
    合成视频：将幻灯片截图和音频合成为视频

    优先使用用户上传的截图，如果不存在则使用 LibreOffice 转换 PPT 为图片。
    """
    task = session.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    # 检查状态
    if task.status not in ["audio_ready", "video_ready"]:
        raise HTTPException(status_code=400, detail="请先完成音频生成")

    # 检查音频文件
    audio_dir = settings.audio_dir / task_id
    if not audio_dir.exists():
        raise HTTPException(status_code=400, detail="音频文件不存在")

    # 检查音频文件数量
    audio_files = list(audio_dir.glob("page_*.mp3"))
    if len(audio_files) < task.slide_count:
        raise HTTPException(status_code=400, detail=f"音频文件不完整，需要 {task.slide_count} 个音频文件")

    # 检查 PPT 文件
    if not task.file_path or not Path(task.file_path).exists():
        raise HTTPException(status_code=400, detail="PPT 文件不存在")

    # 获取截图目录（如果用户上传了截图）
    screenshot_dir = None
    if task.slides_screenshots:
        screenshot_dir = str(settings.static_dir / "screenshots" / task_id)

    # 调用视频合成服务
    try:
        from app.services import synthesize_video
        # 使用原始 PPT 文件名（不含扩展名）
        original_filename = Path(task.filename).stem if task.filename else task_id
        output_path = synthesize_video(task_id, task.file_path, str(audio_dir), screenshot_dir, original_filename)

        # 保存结果
        task.video_path = output_path
        task.status = "video_ready"
        session.commit()

        return {
            "task_id": task_id,
            "video_path": f"/static/video/{task_id}/{Path(output_path).name}",
            "status": task.status
        }
    except ImportError:
        raise HTTPException(status_code=500, detail="未安装 pywin32，无法使用 PowerPoint 自动化")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"视频合成失败: {str(e)}")
