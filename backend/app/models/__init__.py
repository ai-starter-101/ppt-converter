"""数据模型模块"""
from app.models.task import Task, slides_to_json, parse_slides_json

__all__ = ["Task", "slides_to_json", "parse_slides_json"]
