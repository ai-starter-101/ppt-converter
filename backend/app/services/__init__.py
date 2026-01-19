"""服务模块"""
from app.services.ppt_service import extract_text_from_ppt, get_ppt_info
from app.services.script_service import generate_script
from app.services.tts_service import generate_audio, get_audio_duration

__all__ = ["extract_text_from_ppt", "get_ppt_info", "generate_script", "generate_audio", "get_audio_duration"]
