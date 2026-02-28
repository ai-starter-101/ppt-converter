"""TTS 服务 - 文字转语音"""
import asyncio
import base64
import hashlib
import hmac
import json
import logging
import re
import subprocess
import time
import urllib.parse
from pathlib import Path
from typing import List, Dict
import edge_tts
import httpx
from app.config import settings

logger = logging.getLogger(__name__)

# 导入火山引擎双向TTS协议
from app.services.volc_protocol import (
    start_connection,
    finish_connection,
    start_session,
    finish_session,
    task_request,
    wait_for_event,
    receive_message,
    get_resource_id,
    MsgType,
    EventType,
)
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
# 多音字词典 - TTS 容易读错的词
# 注意：避免包含有重叠部分的词，如 "进行" 和 "行"
HOMOPHONE_DICT = {
    # 需要优先处理的词（放在前面）
    "进行": "进形",
    "举行": "举形",
    # 行 (háng vs xíng) - 这些词必须完整匹配才替换
    "换行符": "换航符",
    "换行": "换航",
    "银行": "银航",
    "行业": "航业",
    "行列": "航列",
    "行数": "航数",
    "行高": "航高",
    "行距": "航距",
    "行号": "航号",
    "行首": "航首",
    "行尾": "航尾",
    "行头": "航头",
    "每行": "每航",
    "行内": "航内",
    "行间": "航间",
    "行与行": "航与航",
    # 符号
    "C++": "C加加",
    ">=": "大于等于",
    "<=": "小于等于",
    "==": "等于",
    "&&": "与",
    "||": "或",
}


def fix_homophones(text: str) -> str:
    """修复多音字，将容易读错的词替换为正确的读音"""
    if not text:
        return text

    original_text = text

    # 修复数字+横杠+数字的问题，如 "1-1" 读成 "11"
    # 模式：数字/字母 + - + 数字/字母
    def replace_dash(match):
        left = match.group(1)
        right = match.group(2)
        # 替换为 "左 杠 右" 的形式
        return f"{left} 杠 {right}"

    # 匹配形如 "1-1"、"A-1"、"2024-01"、"v1-2" 等
    text = re.sub(r'([A-Za-z0-9]+)-([A-Za-z0-9]+)', replace_dash, text)

    # 执行多音字替换 - 使用更安全的方式：按长度降序排列，先处理长的词
    sorted_items = sorted(HOMOPHONE_DICT.items(), key=lambda x: len(x[0]), reverse=True)
    for wrong, correct in sorted_items:
        text = text.replace(wrong, correct)

    return text


async def _generate_doubao_audio(text: str, output_path: str) -> float:
    """使用豆包 TTS (火山引擎) 生成音频"""
    if not settings.doubao_app_id or not settings.doubao_access_token:
        raise ValueError("豆包 TTS 配置不完整，需要设置 DOUBAO_APP_ID 和 DOUBAO_ACCESS_TOKEN")

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # 火山引擎 TTS API
    url = "https://openspeech.bytedance.com/api/v1/tts"
    # url = "https://openspeech.bytedance.com/api/v3/tts/unidirectional"

    # 生成唯一请求 ID
    import uuid
    reqid = str(uuid.uuid4())

    # 获取 voice_type（优先使用配置，否则使用豆包2.0默认音色）
    voice_type = settings.tts_voice if settings.tts_voice else "zh_female_shuangkuaisisi_emo_v2_mars_bigtts"

    # 检测是否包含 SSML 标签
    is_ssml = "<speak" in text or "<break" in text or "</speak>" in text

    # 请求体
    payload = {
        "app": {
            "appid": settings.doubao_app_id,
            "token": settings.doubao_access_token,
            "cluster": settings.doubao_cluster,
        },
        "user": {
            "uid": settings.doubao_app_id
        },
        "audio": {
            "voice_type": voice_type,
            "encoding": "mp3",
            "speed_ratio": 1.0,
            "volume_ratio": 1.0,
        },
        "request": {
            "reqid": reqid,
            "text": text,
            "operation": "query",
            "text_type": "ssml" if is_ssml else "plain",  # SSML 支持
        }
    }

    headers = {
        "Authorization": f"Bearer;{settings.doubao_access_token}",
        "Content-Type": "application/json"
    }

    async with httpx.AsyncClient(timeout=120.0) as client:
        logger.info(f"豆包 TTS 请求: text={text[:30]}..., voice={voice_type}")
        response = await client.post(url, headers=headers, json=payload)
        logger.info(f"豆包 TTS 响应: status={response.status_code}, body={response.text[:200]}")

        if response.status_code == 429:
            raise RuntimeError(f"豆包 TTS 限流 (HTTP 429)。响应: {response.text[:200]}")

        if response.status_code != 200:
            raise RuntimeError(f"豆包 TTS 请求失败: HTTP {response.status_code} - {response.text[:200]}")

        result = response.json()
        code = result.get("code", -1)
        message = result.get("message", "")

        if code != 3000:
            error_messages = {
                3001: "配额不足，请充值",
                3002: "参数错误",
                3003: "鉴权失败",
                3004: "请求过于频繁",
                3005: "服务内部错误",
            }
            hint = error_messages.get(code, "")
            raise RuntimeError(f"豆包 TTS 失败 (code={code}): {message} {hint}")

        # 解码音频数据
        audio_data = base64.b64decode(result["data"])
        with open(output_path, "wb") as f:
            f.write(audio_data)

        # 获取时长
        duration_ms = result.get("addition", {}).get("duration", "0")
        return float(duration_ms) / 1000  # 转换为秒


async def _generate_doubao_bidir_audio(text: str, output_path: str) -> float:
    """使用豆包 TTS (火山引擎双向TTS) 生成音频 - 优化版

    优化点：
    - 按句子批量发送（不逐字发送）
    - 添加超时控制
    - 增强错误处理和日志
    """
    if not settings.doubao_app_id or not settings.doubao_access_token:
        raise ValueError("豆包 TTS 配置不完整，需要设置 DOUBAO_APP_ID 和 DOUBAO_ACCESS_TOKEN")

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    import websockets
    import uuid

    endpoint = "wss://openspeech.bytedance.com/api/v3/tts/bidirection"
    connect_id = str(uuid.uuid4())

    # 音色配置
    voice_type = settings.tts_voice if settings.tts_voice else "zh_female_shuangkuaisisi_emo_v2_mars_bigtts"

    headers = {
        "X-Api-App-Key": settings.doubao_app_id,
        "X-Api-Access-Key": settings.doubao_access_token,
        "X-Api-Resource-Id": settings.doubao_resource_id or get_resource_id(voice_type),
        "X-Api-Connect-Id": connect_id,
    }

    logger.info(f"Connecting to Volcano TTS: {endpoint}")
    logger.info(f"Headers: appid={settings.doubao_app_id[:8] if settings.doubao_app_id else 'None'}...")
    logger.info(f"TTS params: speech_rate={settings.tts_speed}, loudness_rate={settings.tts_volume}, pitch={settings.tts_pitch}")

    try:
        # 30秒超时连接
        async with websockets.connect(
            endpoint, additional_headers=headers, max_size=10 * 1024 * 1024,
            open_timeout=60, close_timeout=30
        ) as websocket:
            logid = websocket.response.headers.get('x-tt-logid', 'unknown')
            logger.info(f"Connected to Volcano TTS, logid: {logid}")
            # 1. 开始连接 - 10秒超时
            await asyncio.wait_for(start_connection(websocket), timeout=10)
            await asyncio.wait_for(
                wait_for_event(websocket, MsgType.FullServerResponse, EventType.ConnectionStarted),
                timeout=10
            )

            # 2. 分割文本为句子（支持多种标点符号）
            import re
            # 按句号、问号、感叹号分割（保留原始标点在句子末尾）
            sentences = re.split(r'([。？！])', text)
            # 重新组合句子和标点
            result = []
            i = 0
            while i < len(sentences):
                s = sentences[i].strip()
                if s:
                    # 如果下一项是标点，添加到句子末尾
                    if i + 1 < len(sentences) and sentences[i + 1] in '。？！':
                        s += sentences[i + 1]
                        i += 1
                    result.append(s)
                i += 1
            if not result:
                result = [text]
            sentences = result

            audio_data = bytearray()

            # 3. 会话基础请求
            audio_params = {
                "format": "mp3",
                "sample_rate": 24000,
                "enable_timestamp": True,
            }

            # 添加语速、音量参数到 audio_params（豆包2.0）
            # speech_rate: [-50, 100], 0=标准速度, 100=2倍速, -50=0.5倍速
            # loudness_rate: [-50, 100], 0=标准音量, 100=2倍音量, -50=0.5倍音量
            if settings.tts_speed:
                audio_params["speech_rate"] = int(settings.tts_speed)
            if settings.tts_volume:
                audio_params["loudness_rate"] = int(settings.tts_volume)

            # 添加音调参数到 additions.post_process（豆包2.0）
            # pitch: [-12, 12], 0=标准音调
            additions = {"disable_markdown_filter": False}
            if settings.tts_pitch:
                additions["post_process"] = {"pitch": int(settings.tts_pitch)}

            req_params = {
                "speaker": voice_type,
                "audio_params": audio_params,
                "additions": json.dumps(additions),
            }

            base_request = {
                "user": {"uid": settings.doubao_app_id},
                "namespace": "BidirectionalTTS",
                "req_params": req_params,
            }

            logger.info(f"Full req_params: {json.dumps(req_params, ensure_ascii=False)[:500]}")

            # 4. 处理每个句子
            for i, sentence in enumerate(sentences):
                session_id = str(uuid.uuid4())

                # 4.1 开始会话 - 10秒超时
                start_session_request = base_request.copy()
                start_session_request["event"] = EventType.StartSession
                await asyncio.wait_for(
                    start_session(websocket, json.dumps(start_session_request).encode(), session_id),
                    timeout=10
                )
                await asyncio.wait_for(
                    wait_for_event(websocket, MsgType.FullServerResponse, EventType.SessionStarted),
                    timeout=10
                )

                # 4.2 发送整句文本
                synthesis_request = base_request.copy()
                synthesis_request["event"] = EventType.TaskRequest
                synthesis_request["req_params"]["text"] = sentence
                await task_request(websocket, json.dumps(synthesis_request).encode(), session_id)

                # 4.3 结束会话
                await finish_session(websocket, session_id)

                # 4.4 接收音频数据 - 30秒超时
                msg_count = 0
                while True:
                    msg = await asyncio.wait_for(receive_message(websocket), timeout=60)
                    msg_count += 1

                    if msg.type == MsgType.FullServerResponse:
                        if msg.event == EventType.SessionFinished:
                            break
                    elif msg.type == MsgType.AudioOnlyServer:
                        audio_data.extend(msg.payload)

                logger.debug(f"Sentence {i+1}/{len(sentences)} completed, received {msg_count} messages")

            # 5. 结束连接
            await asyncio.wait_for(finish_connection(websocket), timeout=10)
            await asyncio.wait_for(
                wait_for_event(websocket, MsgType.FullServerResponse, EventType.ConnectionFinished),
                timeout=10
            )

            # 保存音频文件
            if audio_data:
                with open(output_path, "wb") as f:
                    f.write(audio_data)
                logger.debug(f"Audio saved: {len(audio_data)} bytes to {output_path}")
            else:
                raise RuntimeError("未收到音频数据")

    except asyncio.TimeoutError:
        logger.error("Volcano TTS timeout")
        raise RuntimeError("火山引擎 TTS 请求超时，请检查网络连接或代理设置")
    except websockets.exceptions.InvalidStatusCode as e:
        logger.error(f"Volcano TTS connection failed: status={e.status_code}")
        raise RuntimeError(f"火山引擎 TTS 连接失败 (status={e.status_code}): {e}")
    except Exception as e:
        logger.error(f"Volcano TTS error: {type(e).__name__}: {e}")
        raise RuntimeError(f"火山引擎 TTS 失败: {type(e).__name__}: {str(e)}")

    # 获取音频时长
    duration = get_audio_duration(str(output_path))
    return duration


async def generate_audio(text: str, output_path: str) -> float:
    """
    生成音频文件

    根据配置选择 TTS 引擎:
    - "edge": Edge TTS (在线，音质好)
    - "offline": macOS say 命令 (离线，使用 Ting-Ting 语音)
    - "xfyun": 讯飞 TTS (在线，多种语音)
    - "doubao": 豆包 TTS (在线，单向HTTP)
    - "doubao_bidir": 豆包 TTS (火山引擎双向TTS，WebSocket实时流)

    Args:
        text: 要转换的文本
        output_path: 输出文件路径 (.mp3)

    Returns:
        音频时长（秒）
    """
    if not text or not text.strip():
        raise ValueError("文本内容不能为空")

    # 修复多音字问题
    text = fix_homophones(text)

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
    elif tts_engine == 'doubao_bidir':
        # 使用豆包双向TTS (火山引擎WebSocket)
        return await _generate_doubao_bidir_audio(text, str(output_path))
    elif tts_engine == 'doubao':
        # 使用豆包单向HTTP TTS
        return await _generate_doubao_audio(text, str(output_path))
    else:
        # 默认使用 Edge TTS，使用代理 7897 (SOCKS5)
        return await _generate_edge_audio(
            text,
            str(output_path),
            settings.tts_voice,
            "socks5://127.0.0.1:7897"  # SOCKS5 代理端口
        )


async def generate_audio_per_page(
    slides_script: List[Dict],
    audio_dir: str,
    progress_callback=None,
    existing_audios: List[Dict] = None,
    max_concurrent: int = 3
) -> List[Dict]:
    """按页生成音频文件（支持并发）

    Args:
        slides_script: 脚本列表
        audio_dir: 音频输出目录
        progress_callback: 进度回调函数，接收 (current, total, page_num) 参数
        existing_audios: 已有的音频信息列表，用于跳过已成功的页面
        max_concurrent: 最大并发数，默认5路
    """
    Path(audio_dir).mkdir(parents=True, exist_ok=True)
    results = []
    total = len(slides_script)

    # 构建已成功的页面集合
    successful_pages: set = set()
    if existing_audios:
        for audio in existing_audios:
            if audio.get("audio_path") and Path(audio["audio_path"]).exists():
                successful_pages.add(audio["page_num"])

    # 实际需要生成的页面
    scripts_to_generate = [s for s in slides_script if s["page_num"] not in successful_pages]
    generate_total = len(scripts_to_generate)

    if generate_total == 0:
        # 所有页面都已生成完成
        if progress_callback:
            progress_callback(total, total, None)
        return existing_audios or []

    # 添加已成功的结果到最终结果
    for audio in (existing_audios or []):
        if audio["page_num"] in successful_pages:
            results.append(audio)

    # 并发生成音频
    semaphore = asyncio.Semaphore(max_concurrent)
    generated_count = 0
    count_lock = asyncio.Lock()

    async def generate_with_semaphore(slide: Dict) -> Dict:
        """带并发控制的单页音频生成"""
        async with semaphore:
            page_num = slide["page_num"]
            script = slide.get("script", "")

            # 报告进度
            nonlocal generated_count
            async with count_lock:
                generated_count += 1
                if progress_callback:
                    progress_callback(generated_count, generate_total, page_num)

            if not script or script.strip() == "":
                return {
                    "page_num": page_num,
                    "audio_path": None,
                    "duration": 0
                }

            audio_filename = f"page_{page_num}.mp3"
            audio_path = Path(audio_dir) / audio_filename

            try:
                duration = await generate_audio(script, str(audio_path))
                return {
                    "page_num": page_num,
                    "audio_path": str(audio_path),
                    "duration": duration
                }
            except Exception as e:
                return {
                    "page_num": page_num,
                    "audio_path": None,
                    "duration": 0,
                    "error": str(e)
                }

    # 并发执行所有音频生成任务
    tasks = [generate_with_semaphore(slide) for slide in scripts_to_generate]
    results.extend(await asyncio.gather(*tasks))

    # 按页码排序结果
    results.sort(key=lambda x: x["page_num"])

    # 报告完成
    if progress_callback:
        progress_callback(generate_total, generate_total, None)

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
