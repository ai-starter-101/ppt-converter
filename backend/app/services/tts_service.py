"""TTS 服务 - 文字转语音"""
import asyncio
import subprocess
from pathlib import Path
from typing import List, Dict
import edge_tts
from app.config import settings

# 尝试导入 pydub
try:
    from pydub import AudioSegment
    PYDUB_AVAILABLE = True
except ImportError:
    PYDUB_AVAILABLE = False


async def _generate_edge_audio(text: str, output_path: str, voice: str, proxy: str = "") -> float:
    """使用 Edge TTS 生成音频"""
    # 使用代理绕过微软限制
    proxy_url = "http://127.0.0.1:7897" if not proxy else proxy
    communicate = edge_tts.Communicate(text, voice, proxy=proxy_url)
    await communicate.save(output_path)
    return get_audio_duration(output_path)


def _generate_say_audio(text: str, output_path: str) -> float:
    """使用 macOS say 命令生成音频（离线方案）"""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # 使用 Tingting 中文语音
    voice = "Tingting"

    # 先保存为 aiff 格式（say 命令原生支持）
    aiff_path = output_path.with_suffix('.aiff')

    try:
        # 使用 say 命令直接输出为 AIFF
        subprocess.run(
            ['say', '-v', voice, '-o', str(aiff_path), text],
            capture_output=True,
            check=True
        )

        # 检查文件
        if not aiff_path.exists() or aiff_path.stat().st_size < 1000:
            raise RuntimeError("say 命令未能生成音频文件")

        # 如果有 pydub，转换为 MP3
        if PYDUB_AVAILABLE:
            audio = AudioSegment.from_file(str(aiff_path))
            audio.export(str(output_path), format="mp3")
            aiff_path.unlink()
        else:
            # 没有 pydub，直接重命名
            aiff_path.rename(output_path)

        # 获取实际时长
        duration = get_audio_duration(str(output_path))
        return duration

    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"say 命令执行失败: {e.stderr.decode()}")


async def generate_audio(text: str, output_path: str) -> float:
    """
    生成音频文件

    根据配置选择 TTS 引擎:
    - "edge": Edge TTS (在线，音质好)
    - "offline": macOS say 命令 (离线，使用 Ting-Ting 语音)

    Args:
        text: 要转换的文本
        output_path: 输出文件路径 (.mp3)

    Returns:
        音频时长（秒）
    """
    if not text or not text.strip():
        raise ValueError("文本内容不能为空")

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    tts_engine = getattr(settings, 'tts_engine', 'edge')

    if tts_engine == 'offline':
        # 使用 macOS say 命令
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            lambda: _generate_say_audio(text, str(output_path))
        )
    else:
        # 默认使用 Edge TTS，使用代理 7897 (SOCKS5)
        return await _generate_edge_audio(
            text,
            str(output_path),
            settings.tts_voice,
            "socks5://127.0.0.1:7897"  # SOCKS5 代理端口
        )


async def generate_audio_per_page(slides_script: List[Dict], audio_dir: str) -> List[Dict]:
    """按页生成音频文件"""
    Path(audio_dir).mkdir(parents=True, exist_ok=True)
    results = []

    for slide in slides_script:
        page_num = slide["page_num"]
        script = slide.get("script", "")

        if not script or script.strip() == "":
            results.append({
                "page_num": page_num,
                "audio_path": None,
                "duration": 0
            })
            continue

        audio_filename = f"page_{page_num}.mp3"
        audio_path = Path(audio_dir) / audio_filename

        try:
            duration = await generate_audio(script, str(audio_path))
            results.append({
                "page_num": page_num,
                "audio_path": str(audio_path),
                "duration": duration
            })
        except Exception as e:
            results.append({
                "page_num": page_num,
                "audio_path": None,
                "duration": 0,
                "error": str(e)
            })

    return results


def get_audio_duration(audio_path: str) -> float:
    """获取音频文件时长"""
    if not Path(audio_path).exists():
        raise FileNotFoundError(f"音频文件不存在: {audio_path}")

    try:
        from mutagen.mp4 import MP4
        audio = MP4(audio_path)
        return audio.info.length
    except Exception:
        try:
            from mutagen.mp3 import MP3
            audio = MP3(audio_path)
            return audio.info.length
        except Exception:
            if PYDUB_AVAILABLE:
                try:
                    audio = AudioSegment.from_file(audio_path)
                    return len(audio) / 1000
                except Exception:
                    pass
            import os
            file_size = os.path.getsize(audio_path)
            return file_size / 16000
