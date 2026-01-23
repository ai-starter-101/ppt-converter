"""TTS 服务 - 文字转语音"""
import asyncio
import base64
import hashlib
import hmac
import json
import subprocess
import time
import urllib.parse
from pathlib import Path
from typing import List, Dict
import edge_tts
import httpx
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


# 讯飞 TTS 配置
XFYUN_BASE_URL = "wss://cbm01.cn-huabei-1.xf-yun.com/v1/private/med95e8a8"


def _generate_xfyun_signature(app_id: str, api_key: str, api_secret: str) -> tuple:
    """生成讯飞 API 签名"""
    now = time.strftime('%a, %d %b %Y %H:%M:%S GMT', time.gmtime())
    signature_raw = f"host: cbm01.cn-huabei-1.xf-yun.com\ndate: {now}\nGET /v1/private/med95e8a8 HTTP/1.1"
    signature_sha = hmac.new(
        api_secret.encode('utf-8'),
        signature_raw.encode('utf-8'),
        hashlib.sha256
    ).digest()
    authorization_raw = f'api_key="{api_key}", algorithm="hmac-sha256", headers="host date request-line", signature="{base64.b64encode(signature_sha).decode()}"'
    authorization = base64.b64encode(authorization_raw.encode('utf-8')).decode()
    return authorization, now


async def _generate_xfyun_audio(text: str, output_path: str) -> float:
    """使用讯飞 TTS 生成音频"""
    if not settings.xfyun_app_id or not settings.xfyun_api_key or not settings.xfyun_api_secret:
        raise ValueError("讯飞 TTS 配置不完整，需要设置 XFYUN_APP_ID, XFYUN_API_KEY, XFYUN_API_SECRET")

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # 生成签名
    authorization, date_str = _generate_xfyun_signature(
        settings.xfyun_app_id,
        settings.xfyun_api_key,
        settings.xfyun_api_secret
    )

    # 讯飞请求参数
    payload = {
        "common": {"app_id": settings.xfyun_app_id},
        "business": {
            "aue": "lame",  # 输出 MP3
            "vcn": settings.tts_voice if settings.tts_voice else "xiaoyan",  # 语音名称
            "speed": 50,  # 语速
            "volume": 50,  # 音量
            "pitch": 50,  # 音调
        },
        "data": {
            "text": base64.b64encode(text.encode('utf-8')).decode(),
            "status": 2,
        }
    }

    # 使用 WebSocket 连接
    try:
        import websockets
        ws_url = f"{XFYUN_BASE_URL}?authorization={urllib.parse.quote(authorization)}&date={urllib.parse.quote(date_str)}&host=cbm01.cn-huabei-1.xf-yun.com"

        async with websockets.connect(ws_url) as websocket:
            await websocket.send(json.dumps(payload))
            response = await websocket.recv()
            result = json.loads(response)

            if result.get("code") != 0:
                raise RuntimeError(f"讯飞 TTS 失败: {result.get('message')}")

            # 解码音频
            audio_data = base64.b64decode(result["data"]["audio"])
            with open(output_path, "wb") as f:
                f.write(audio_data)

    except ImportError:
        # 如果没有 websockets 库，使用 HTTP API
        raise RuntimeError("需要安装 websockets 库才能使用讯飞 TTS: pip install websockets")

    return get_audio_duration(str(output_path))


async def _generate_doubao_audio(text: str, output_path: str) -> float:
    """使用豆包 TTS (火山引擎) 生成音频"""
    if not settings.doubao_app_id or not settings.doubao_access_token:
        raise ValueError("豆包 TTS 配置不完整，需要设置 DOUBAO_APP_ID 和 DOUBAO_ACCESS_TOKEN")

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # 火山引擎 TTS API
    url = "https://openspeech.bytedance.com/api/v1/tts"

    # 生成唯一请求 ID
    import uuid
    reqid = str(uuid.uuid4())

    # 请求体
    payload = {
        "app": {
            "appid": settings.doubao_app_id,
            "token": settings.doubao_access_token,
            "cluster": settings.doubao_cluster,
        },
        "user": {
            "uid": settings.doubao_app_id  # 使用 appid 作为 uid
        },
        "audio": {
            "voice_type": settings.tts_voice if settings.tts_voice else "zh_female_vv_venus_mars_bigtts",
            "encoding": "mp3",
            "speed_ratio": 1.0,
        },
        "request": {
            "reqid": reqid,
            "text": text,
            "operation": "query",  # HTTP 方式只能用 query
        }
    }

    headers = {
        "Authorization": f"Bearer;{settings.doubao_access_token}",
        "Content-Type": "application/json"
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(url, headers=headers, json=payload, timeout=60.0)

        if response.status_code != 200:
            raise RuntimeError(f"豆包 TTS 请求失败: {response.status_code} - {response.text}")

        result = response.json()

        # 检查返回码
        code = result.get("code", -1)
        if code != 3000:
            message = result.get("message", "未知错误")
            raise RuntimeError(f"豆包 TTS 失败 (code={code}): {message}")

        # 解码音频数据
        audio_data = base64.b64decode(result["data"])
        with open(output_path, "wb") as f:
            f.write(audio_data)

        # 获取时长
        duration_ms = result.get("addition", {}).get("duration", "0")
        return float(duration_ms) / 1000  # 转换为秒


async def generate_audio(text: str, output_path: str) -> float:
    """
    生成音频文件

    根据配置选择 TTS 引擎:
    - "edge": Edge TTS (在线，音质好)
    - "offline": macOS say 命令 (离线，使用 Ting-Ting 语音)
    - "xfyun": 讯飞 TTS (在线，多种语音)
    - "doubao": 豆包 TTS (在线)

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
    elif tts_engine == 'xfyun':
        # 使用讯飞 TTS
        return await _generate_xfyun_audio(text, str(output_path))
    elif tts_engine == 'doubao':
        # 使用豆包 TTS
        return await _generate_doubao_audio(text, str(output_path))
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
