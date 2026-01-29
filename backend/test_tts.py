#!/usr/bin/env python3
"""测试火山引擎双向 TTS"""
import asyncio
import sys
sys.path.insert(0, '.')

from app.services.volc_protocol import (
    start_connection, finish_connection, start_session, finish_session,
    task_request, wait_for_event, receive_message, get_resource_id,
    MsgType, EventType
)
from app.config import settings
import websockets
import uuid
import json

async def test_tts():
    print("=" * 50)
    print("测试火山引擎双向 TTS")
    print("=" * 50)

    # 打印配置
    print(f"\n配置检查:")
    print(f"  doubao_app_id: {settings.doubao_app_id[:8] if settings.doubao_app_id else 'None'}...")
    print(f"  doubao_access_token: {settings.doubao_access_token[:8] if settings.doubao_access_token else 'None'}...")
    print(f"  tts_voice: {settings.tts_voice}")

    endpoint = "wss://openspeech.bytedance.com/api/v3/tts/bidirection"
    voice_type = "zh_female_shuangkuaisisi_emo_v2_mars_bigtts"
    connect_id = str(uuid.uuid4())

    headers = {
        "X-Api-App-Key": settings.doubao_app_id,
        "X-Api-Access-Key": settings.doubao_access_token,
        "X-Api-Resource-Id": get_resource_id(voice_type),
        "X-Api-Connect-Id": connect_id,
    }

    print(f"   Resource ID: {headers['X-Api-Resource-Id']}")

    print(f"\n1. 连接 WebSocket...")
    try:
        async with websockets.connect(
            endpoint, additional_headers=headers, open_timeout=30, close_timeout=10
        ) as ws:
            logid = ws.response.headers.get('x-tt-logid', 'unknown')
            print(f"   ✓ 连接成功, logid: {logid}")

            print(f"\n2. 发送 StartConnection...")
            await start_connection(ws)
            print(f"   ✓ 发送成功")

            print(f"\n3. 等待 ConnectionStarted...")
            msg = await asyncio.wait_for(
                wait_for_event(ws, MsgType.FullServerResponse, EventType.ConnectionStarted),
                timeout=10
            )
            print(f"   ✓ 收到响应: {msg.event}")

            # 测试文本
            text = "你好，这是测试。"
            print(f"\n4. 处理文本: '{text}'")

            sentences = [s.strip() + "。" for s in text.split("。") if s.strip()]
            if not sentences:
                sentences = [text]
            print(f"   句子列表: {sentences}")

            audio_data = bytearray()

            base_request = {
                "user": {"uid": settings.doubao_app_id},
                "namespace": "BidirectionalTTS",
                "req_params": {
                    "speaker": voice_type,
                    "audio_params": {
                        "format": "mp3",
                        "sample_rate": 24000,
                        "enable_timestamp": True,
                    },
                    "additions": json.dumps({"disable_markdown_filter": False}),
                },
            }

            for i, sentence in enumerate(sentences):
                print(f"\n5.{i+1} 处理句子: '{sentence}'")
                session_id = str(uuid.uuid4())

                print(f"   5.{i+1}.1 StartSession...")
                start_req = base_request.copy()
                start_req["event"] = EventType.StartSession
                await start_session(ws, json.dumps(start_req).encode(), session_id)
                msg = await asyncio.wait_for(
                    wait_for_event(ws, MsgType.FullServerResponse, EventType.SessionStarted),
                    timeout=10
                )
                print(f"       ✓ 收到 SessionStarted")

                print(f"   5.{i+1}.2 发送文本...")
                task_req = base_request.copy()
                task_req["event"] = EventType.TaskRequest
                task_req["req_params"]["text"] = sentence
                await task_request(ws, json.dumps(task_req).encode(), session_id)
                print(f"       ✓ 文本已发送")

                print(f"   5.{i+1}.3 FinishSession...")
                await finish_session(ws, session_id)

                print(f"   5.{i+1}.4 等待音频数据 (30s超时)...")
                msg_count = 0
                while True:
                    msg = await asyncio.wait_for(receive_message(ws), timeout=30)
                    msg_count += 1
                    print(f"       收到消息: type={msg.type}, event={msg.event}, payload_size={len(msg.payload)}")

                    # 检查错误消息
                    if msg.type == MsgType.Error:
                        error_payload = msg.payload.decode('utf-8', errors='ignore')
                        print(f"       ✗ 错误详情: {error_payload}")
                        raise Exception(f"Server error: {error_payload}")

                    if msg.type == MsgType.FullServerResponse:
                        if msg.event == EventType.SessionFinished:
                            print(f"       ✓ SessionFinished")
                            break
                    elif msg.type == MsgType.AudioOnlyServer:
                        audio_data.extend(msg.payload)
                        print(f"       ✓ 收到音频数据, 累计: {len(audio_data)} bytes")

            print(f"\n6. FinishConnection...")
            await finish_connection(ws)
            msg = await asyncio.wait_for(
                wait_for_event(ws, MsgType.FullServerResponse, EventType.ConnectionFinished),
                timeout=10
            )
            print(f"   ✓ 收到 ConnectionFinished")

            if audio_data:
                output_path = "/tmp/test_output.mp3"
                with open(output_path, "wb") as f:
                    f.write(audio_data)
                print(f"\n✓ 成功! 音频保存到 {output_path}, 大小: {len(audio_data)} bytes")
            else:
                print(f"\n✗ 未收到音频数据")

    except asyncio.TimeoutError:
        print(f"\n✗ 超时错误")
    except Exception as e:
        print(f"\n✗ 错误: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    asyncio.run(test_tts())
