"""任务相关 API 路由"""
import uuid
from pathlib import Path
from typing import List, Optional
from fastapi import APIRouter, HTTPException, UploadFile, File, Depends
from sqlmodel import Session, select
from app.database import get_session
from app.models import Task
from app.services import extract_text_from_ppt, get_ppt_info, generate_script, generate_audio, get_audio_duration
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

    # 验证文件
    try:
        ppt_info = get_ppt_info(str(file_path))
    except Exception as e:
        file_path.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail=f"无效的 PPT 文件: {str(e)}")

    # 更新任务
    task.filename = file.filename
    task.file_path = str(file_path)
    task.status = "uploaded"
    session.commit()

    return {
        "id": task.id,
        "filename": task.filename,
        "status": task.status,
        "slide_count": ppt_info["slide_count"]
    }


@router.post("/{task_id}/script")
async def generate_script_endpoint(
    task_id: str,
    session: Session = Depends(get_session)
) -> dict:
    """生成讲解脚本"""
    task = session.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    if task.status != "uploaded":
        raise HTTPException(status_code=400, detail="请先上传 PPT 文件")

    # 提取 PPT 内容
    try:
        ppt_content = extract_text_from_ppt(task.file_path)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"解析 PPT 失败: {str(e)}")

    # 生成脚本
    try:
        script = await generate_script(ppt_content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"生成脚本失败: {str(e)}")

    # 更新任务
    task.script = script
    task.status = "script_ready"
    session.commit()

    return {
        "id": task.id,
        "script": task.script,
        "status": task.status
    }


@router.put("/{task_id}/script")
async def update_script(
    task_id: str,
    script_data: dict,
    session: Session = Depends(get_session)
) -> dict:
    """更新脚本内容"""
    task = session.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    task.script = script_data.get("script", "")
    session.commit()

    return {"id": task.id, "script": task.script, "status": task.status}


@router.post("/{task_id}/audio")
async def generate_audio_endpoint(
    task_id: str,
    session: Session = Depends(get_session)
) -> dict:
    """生成音频"""
    task = session.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    if task.status != "script_ready":
        raise HTTPException(status_code=400, detail="请先生成或编辑脚本")

    if not task.script:
        raise HTTPException(status_code=400, detail="脚本内容为空")

    # 生成音频文件
    audio_filename = f"{task_id}.mp3"
    audio_path = settings.audio_dir / audio_filename
    settings.audio_dir.mkdir(parents=True, exist_ok=True)

    try:
        duration = await generate_audio(task.script, str(audio_path))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"生成音频失败: {str(e)}")

    # 更新任务
    task.audio_path = str(audio_path)
    task.audio_duration = duration
    task.status = "audio_ready"
    session.commit()

    return {
        "id": task.id,
        "audio_path": f"/static/audio/{audio_filename}",
        "audio_duration": duration,
        "status": task.status
    }


@router.get("/{task_id}/audio")
async def get_audio(task_id: str, session: Session = Depends(get_session)):
    """获取音频文件流"""
    task = session.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    if not task.audio_path or not Path(task.audio_path).exists():
        raise HTTPException(status_code=404, detail="音频文件不存在")

    from fastapi.responses import FileResponse
    return FileResponse(
        path=task.audio_path,
        media_type="audio/mpeg",
        filename=f"{task_id}.mp3"
    )
