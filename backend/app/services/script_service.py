"""LLM 服务 - 生成讲解脚本"""
import json
import os
from typing import List, Dict
import httpx
from app.config import settings


def get_http_client_kwargs() -> Dict:
    """获取 HTTP 客户端配置"""
    kwargs = {
        "timeout": 120.0,
    }
    # 如果有代理配置，添加代理
    proxy = os.getenv("HTTPS_PROXY") or os.getenv("HTTP_PROXY") or os.getenv("https_proxy") or os.getenv("http_proxy")
    if proxy:
        kwargs["proxy"] = proxy
    return kwargs


async def call_claude_api(messages: List[Dict]) -> str:
    """调用 Claude API"""
    kwargs = get_http_client_kwargs()
    async with httpx.AsyncClient(**kwargs) as client:
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
    kwargs = get_http_client_kwargs()
    async with httpx.AsyncClient(**kwargs) as client:
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
    使用 LLM 生成讲解脚本（完整版本）

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
4. 脚本总长度适中

PPT 内容：
---
{ppt_content}
---

请直接返回讲解脚本。"""

    messages = [{"role": "user", "content": prompt}]

    if settings.llm_provider == "claude":
        return await call_claude_api(messages)
    elif settings.llm_provider == "zhipu":
        return await call_zhipu_api(messages)
    else:
        raise ValueError(f"不支持的 LLM provider: {settings.llm_provider}")


async def generate_script_per_page(slides: List[Dict]) -> List[Dict]:
    """
    按页生成讲解脚本

    Args:
        slides: 每页幻灯片内容 [{"page_num": 1, "content": "xxx"}, ...]

    Returns:
        每页脚本 [{"page_num": 1, "script": "xxx"}, ...]
    """
    results = []

    for slide in slides:
        page_num = slide["page_num"]
        content = slide["content"]

        # 如果内容为空或只有占位符，跳过
        if not content or content.strip() == "[无文本内容]":
            results.append({
                "page_num": page_num,
                "script": ""
            })
            continue

        prompt = f"""请为以下 PPT 幻灯片内容生成一段讲解脚本。

要求：
1. 脚本要口语化、自然
2. 长度适中，约 100-300 字
3. 直接返回脚本内容，不要添加标题

幻灯片 {page_num} 内容：
---
{content}
---

请直接返回讲解脚本："""

        messages = [{"role": "user", "content": prompt}]

        try:
            if settings.llm_provider == "claude":
                script = await call_claude_api(messages)
            elif settings.llm_provider == "zhipu":
                script = await call_zhipu_api(messages)
            else:
                raise ValueError(f"不支持的 LLM provider: {settings.llm_provider}")

            results.append({
                "page_num": page_num,
                "script": script.strip()
            })
        except Exception as e:
            results.append({
                "page_num": page_num,
                "script": f"[脚本生成失败: {str(e)}]"
            })

    return results
