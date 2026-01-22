"""任务数据模型"""
import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
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
    # 幻灯片数量
    slide_count: int = Field(default=0, description="幻灯片总数")

    # 分页数据 - 使用 JSON 字符串存储
    # slides_content: [{"page_num": 1, "content": "xxx"}, ...]
    slides_content: Optional[str] = Field(default=None, description="每页幻灯片内容(JSON)")

    # slides_script: [{"page_num": 1, "script": "xxx"}, ...]
    slides_script: Optional[str] = Field(default=None, description="每页脚本内容(JSON)")

    # 单个完整脚本（兼容旧版本）
    script: Optional[str] = Field(default=None, description="完整脚本内容")

    # 每页音频路径: [{"page_num": 1, "audio_path": "xxx", "duration": 10.5}, ...]
    slides_audio: Optional[str] = Field(default=None, description="每页音频信息(JSON)")

    # 合并后的完整音频
    audio_path: Optional[str] = Field(default=None, max_length=500, description="完整音频文件路径")
    audio_duration: Optional[float] = Field(default=None, description="完整音频时长(秒)")

    created_at: datetime = Field(default_factory=datetime.utcnow, description="创建时间")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="更新时间")

    class Config:
        from_attributes = True


def parse_slides_json(json_str: Optional[str]) -> List[Dict[str, Any]]:
    """解析 JSON 字符串为列表"""
    import json
    if not json_str:
        return []
    try:
        return json.loads(json_str)
    except json.JSONDecodeError:
        return []


def slides_to_json(slides: List[Dict[str, Any]]) -> Optional[str]:
    """将列表转为 JSON 字符串"""
    import json
    if not slides:
        return None
    return json.dumps(slides, ensure_ascii=False)
