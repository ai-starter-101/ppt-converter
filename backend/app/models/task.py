"""任务数据模型"""
import uuid
from datetime import datetime
from typing import Optional
from sqlmodel import Field, SQLModel


class Task(SQLModel, table=True):
    """PPT转换任务模型"""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    filename: str = Field(max_length=255, description="原始文件名")
    file_path: str = Field(max_length=500, description="PPT文件存储路径")
    status: str = Field(
        default="pending",
        max_length=20,
        description="任务状态: pending/uploaded/processing/script_ready/audio_ready/failed"
    )
    script: Optional[str] = Field(default=None, description="讲解脚本内容")
    audio_path: Optional[str] = Field(default=None, max_length=500, description="音频文件路径")
    audio_duration: Optional[float] = Field(default=None, description="音频时长(秒)")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="创建时间")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="更新时间")

    class Config:
        from_attributes = True
