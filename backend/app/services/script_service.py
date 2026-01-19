"""LLM 服务 - 生成讲解脚本"""
import json
from typing import List, Dict, Optional
import httpx
from app.config import settings


async def call_claude_api(messages: List[Dict]) -> str:
    """调用 Claude API"""
    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(
            f"{settings.llm_base_url}/messages",
            headers={
                "Authorization": f"Bearer {settings.llm_api_key}",
                "Content-Type": "application/json",
                "Anthropic-Version": "2023-06-01",
            },
            json={
                "model": settings.llm_model,
                "max_tokens": 4096,
                "messages": messages,
            },
        )
        response.raise_for_status()
        data = response.json()
        return data["content"][0]["text"]


async def call_zhipu_api(messages: List[Dict]) -> str:
    """调用智谱AI (ChatGLM) API"""
    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(
            f"{settings.llm_base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {settings.llm_api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": settings.llm_model,
                "messages": messages,
            },
        )
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]


async def generate_script(ppt_content: str) -> str:
    """
    使用 LLM 生成讲解脚本

    Args:
        ppt_content: 从 PPT 提取的文本内容

    Returns:
        生成的讲解脚本（Markdown 格式）
    """
    prompt = f"""请根据以下 PPT 内容，生成一份讲解脚本。

要求：
1. 脚本要口语化，适合演讲
2. 每页 PPT 对应一段讲解，用 Markdown 二级标题标记（如 "## 第 1 页"）
3. 保持专业但易懂
4. 脚本总长度适中，不要太长也不要太短

PPT 内容：
---
{ppt_content}
---

请直接返回讲解脚本，不要添加其他说明。"""

    messages = [{"role": "user", "content": prompt}]

    if settings.llm_provider == "claude":
        return await call_claude_api(messages)
    elif settings.llm_provider == "zhipu":
        return await call_zhipu_api(messages)
    else:
        raise ValueError(f"不支持的 LLM provider: {settings.llm_provider}")
