"""配置管理模块"""
from functools import lru_cache
from pathlib import Path
import os
from dotenv import load_dotenv


# 加载 .env 文件
load_dotenv()


class Settings:
    """应用配置"""

    # Server
    host: str = os.getenv("HOST", "0.0.0.0")
    port: int = int(os.getenv("PORT", "8000"))
    debug: bool = os.getenv("DEBUG", "false").lower() == "true"

    # Database
    database_url: str = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./data/app.db")

    # LLM
    llm_api_key: str = os.getenv("LLM_API_KEY", "")
    llm_base_url: str = os.getenv("LLM_BASE_URL", "https://api.openai.com/v1")
    llm_model: str = os.getenv("LLM_MODEL", "claude-3-sonnet-20240229")
    llm_provider: str = os.getenv("LLM_PROVIDER", "claude")  # claude 或 zhipu

    # TTS
    tts_voice: str = os.getenv("TTS_VOICE", "zh-CN-XiaoxiaoNeural")

    # Paths - 转为绝对路径
    @property
    def upload_dir(self) -> Path:
        return Path(__file__).parent.parent / os.getenv("UPLOAD_DIR", "static/uploads")

    @property
    def audio_dir(self) -> Path:
        return Path(__file__).parent.parent / os.getenv("AUDIO_DIR", "static/audio")

    @property
    def static_dir(self) -> Path:
        return Path(__file__).parent.parent / os.getenv("STATIC_DIR", "static")


@lru_cache()
def get_settings() -> Settings:
    """获取应用配置（单例模式）"""
    return Settings()


settings = get_settings()
