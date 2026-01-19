"""TTS 服务 - 文字转语音"""
import asyncio
from pathlib import Path
import edge_tts
from app.config import settings


async def _generate_audio_async(text: str, output_path: str, voice: str) -> float:
    """
    异步生成音频文件

    Args:
        text: 要转换的文本
        output_path: 输出文件路径
        voice: 语音名称

    Returns:
        音频时长（秒）
    """
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(output_path)

    # 获取音频时长
    return await _get_audio_duration_async(output_path)


async def _get_audio_duration_async(audio_path: str) -> float:
    """
    异步获取音频时长

    Args:
        audio_path: 音频文件路径

    Returns:
        音频时长（秒）
    """
    import librosa

    duration = await asyncio.to_thread(librosa.get_duration, path=audio_path)
    return duration


async def generate_audio(text: str, output_path: str) -> float:
    """
    使用 Edge TTS 生成音频文件

    Args:
        text: 要转换的文本
        output_path: 输出文件路径（.mp3）

    Returns:
        音频时长（秒）

    Raises:
        ValueError: 文本为空或输出路径无效
    """
    if not text or not text.strip():
        raise ValueError("文本内容不能为空")

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    return await _generate_audio_async(text, str(output_path), settings.tts_voice)


def get_audio_duration(audio_path: str) -> float:
    """
    获取音频文件时长（同步版本）

    Args:
        audio_path: 音频文件路径

    Returns:
        音频时长（秒）
    """
    import librosa

    if not Path(audio_path).exists():
        raise FileNotFoundError(f"音频文件不存在: {audio_path}")

    return librosa.get_duration(path=audio_path)
