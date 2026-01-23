"""服务模块"""
from app.services.ppt_service import (
    extract_text_from_ppt,
    extract_all_text_from_ppt,
    get_ppt_info,
    generate_slide_screenshots_async
)
from app.services.script_service import (
    generate_script,
    generate_script_per_page
)
from app.services.tts_service import (
    generate_audio,
    generate_audio_per_page,
    get_audio_duration
)

__all__ = [
    "extract_text_from_ppt",
    "extract_all_text_from_ppt",
    "get_ppt_info",
    "generate_slide_screenshots_async",
    "generate_script",
    "generate_script_per_page",
    "generate_audio",
    "generate_audio_per_page",
    "get_audio_duration"
]
