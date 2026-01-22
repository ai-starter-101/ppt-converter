"""任务相关 API 路由"""
import uuid
import json
from pathlib import Path
from typing import List, Optional
from fastapi import APIRouter, HTTPException, UploadFile, File, Depends, Query
from sqlmodel import Session, select
from app.database import get_session
from app.models import Task, slides_to_json, parse_slides_json
from app.services import (
    extract_text_from_ppt,
    get_ppt_info,
    generate_script_per_page,
    generate_audio,
    generate_audio_per_page,
    get_audio_duration
)
from app.config import settings
import aiofiles

router = APIRouter(prefix="/api/tasks", tags=["任务管理"])


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
    return task.model_dump()


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

    # 更新任务
    task.filename = file.filename
    task.file_path = str(file_path)
    task.status = "uploaded"
    task.slide_count = ppt_info["slide_count"]
    task.slides_content = slides_to_json(slides_content)
    session.commit()

    return {
        "id": task.id,
        "filename": task.filename,
        "status": task.status,
        "slide_count": task.slide_count,
        "slides": slides_content
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

    # 合并数据
    result = []
    for slide in slides:
        page_num = slide["page_num"]
        script = next((s["script"] for s in scripts if s["page_num"] == page_num), "")
        audio = next((a for a in audios if a["page_num"] == page_num), None)

        result.append({
            "page_num": page_num,
            "content": slide["content"],
            "script": script,
            "audio": audio
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
    return FileResponse(
        path=str(audio_path),
        media_type="audio/mpeg",
        filename=f"{task_id}_page_{page_num}.mp3"
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
        raise HTTPException(status_code=400, detail="请先生成脚本")

    scripts = parse_slides_json(task.slides_script)

    # 过滤有脚本的页面
    valid_scripts = [s for s in scripts if s.get("script", "").strip()]

    if not valid_scripts:
        raise HTTPException(status_code=400, detail="没有可生成音频的脚本")

    # 按页生成音频
    audio_dir = settings.audio_dir / task_id
    audio_results = await generate_audio_per_page(valid_scripts, str(audio_dir))

    task.slides_audio = slides_to_json(audio_results)
    task.status = "audio_ready"
    session.commit()

    return {
        "task_id": task_id,
        "audios": audio_results,
        "status": task.status
    }
