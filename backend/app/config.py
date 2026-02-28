"""配置管理模块"""
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
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./data/app.db")

    # LLM
    llm_api_key: str = os.getenv("LLM_API_KEY", "")
    llm_base_url: str = os.getenv("LLM_BASE_URL", "https://api.openai.com/v1")
    llm_model: str = os.getenv("LLM_MODEL", "claude-3-sonnet-20240229")
    llm_provider: str = os.getenv("LLM_PROVIDER", "claude")  # claude 或 zhipu

    # TTS
    tts_engine: str = os.getenv("TTS_ENGINE", "edge")  # edge, offline, xfyun, doubao
    tts_voice: str = os.getenv("TTS_VOICE", "zh-CN-XiaoxiaoNeural")
    tts_proxy: str = os.getenv("TTS_PROXY", "")  # Edge TTS 代理

    # TTS 音色参数 (豆包2.0)
    # speech_rate: 语速，取值范围[-50,100]，0=标准速度，100=2倍速，-50=0.5倍速
    # loudness_rate: 音量，取值范围[-50,100]，0=标准音量，100=2倍音量，-50=0.5倍音量
    # pitch: 音调，取值范围[-12,12]，0=标准音调
    tts_speed: str = os.getenv("TTS_SPEED", "")    # 语速，如 "0"（标准），"50"（1.5倍），"-25"（0.75倍）
    tts_volume: str = os.getenv("TTS_VOLUME", "")  # 音量，如 "0"（标准），"50"（1.5倍），"-25"（0.75倍）
    tts_pitch: str = os.getenv("TTS_PITCH", "")    # 音调，如 "0"（标准），"-6"（低6度），"6"（高6度）

    # 讯飞 TTS 配置
    xfyun_app_id: str = os.getenv("XFYUN_APP_ID", "")
    xfyun_api_key: str = os.getenv("XFYUN_API_KEY", "")
    xfyun_api_secret: str = os.getenv("XFYUN_API_SECRET", "")

    # 豆包 TTS 配置 (火山引擎)
    doubao_app_id: str = os.getenv("DOUBAO_APP_ID", "")
    doubao_access_token: str = os.getenv("DOUBAO_ACCESS_TOKEN", "")
    doubao_cluster: str = os.getenv("DOUBAO_CLUSTER", "volcano_tts")
    doubao_resource_id: str = os.getenv("DOUBAO_RESOURCE_ID", "volc.service_type.10029")

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


def get_settings() -> Settings:
    """获取应用配置"""
    return Settings()


settings = get_settings()
