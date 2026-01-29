#!/usr/bin/env python3
"""测试火山引擎 HTTP TTS API"""
import asyncio
import httpx
import base64
from dotenv import load_dotenv
import os

load_dotenv()

APP_ID = os.getenv("DOUBAO_APP_ID", "")
ACCESS_TOKEN = os.getenv("DOUBAO_ACCESS_TOKEN", "")
CLUSTER = os.getenv("DOUBAO_CLUSTER", "volcano_tts")
VOICE = os.getenv("TTS_VOICE", "zh_female_shuangkuaisisi_emo_v2_mars_bigtts")

print("=" * 50)
print("火山引擎 HTTP TTS 诊断")
print("=" * 50)
print(f"APP_ID: {APP_ID[:8]}...")
print(f"ACCESS_TOKEN: {ACCESS_TOKEN[:8]}...")
print(f"CLUSTER: {CLUSTER}")
print(f"VOICE: {VOICE}")
print()

async def test_tts():
    url = "https://openspeech.bytedance.com/api/v1/tts"

    payload = {
        "app": {
            "appid": APP_ID,
            "token": ACCESS_TOKEN,
            "cluster": CLUSTER,
        },
        "user": {
            "uid": APP_ID
        },
        "audio": {
            "voice_type": VOICE,
            "encoding": "mp3",
            "speed_ratio": 1.0,
            "volume_ratio": 1.0,
        },
        "request": {
            "reqid": "test-123",
            "text": "你好，这是测试。",
            "operation": "query",
        }
    }

    headers = {
        "Authorization": f"Bearer;{ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }

    print("1. 发送请求...")
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.post(url, headers=headers, json=payload)
            print(f"   状态码: {response.status_code}")
            print(f"   响应头: {dict(response.headers)}")

            if response.status_code == 200:
                result = response.json()
                print(f"   响应体: {result}")
                code = result.get("code", -1)
                if code == 3000:
                    data_size = len(result.get("data", ""))
                    print(f"   ✓ 成功! 音频数据大小: {data_size} bytes")
                else:
                    print(f"   ✗ 业务错误 (code={code}): {result.get('message')}")
            else:
                print(f"   ✗ HTTP错误: {response.text[:200]}")

        except httpx.TimeoutException:
            print("   ✗ 请求超时")
        except Exception as e:
            print(f"   ✗ 异常: {type(e).__name__}: {e}")

if __name__ == "__main__":
    asyncio.run(test_tts())
