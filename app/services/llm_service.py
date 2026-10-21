# 配置大模型客户端（用标准 SDK）不再用 httpx 手搓流式请求了，企业级标准是用 openai 官方的 SDK（因为 DeepSeek 兼容它）。
# app/services/llm_service.py
from openai import AsyncOpenAI

from app.core.config import settings

# 初始化异步客户端 (DeepSeek 兼容 OpenAI 协议)
client = AsyncOpenAI(
    api_key=settings.LLM_API_KEY,
    base_url=settings.LLM_BASE_URL
)

async def chat_stream(messages: list[dict]):
    """封装 LLM 流式调用"""
    response = await client.chat.completions.create(
        model=settings.LLM_MODEL,
        messages=messages,
        stream=True,
    )
    async for chunk in response:
        if chunk.choices[0].delta.content:
            yield chunk.choices[0].delta.content

async def chat_sync(messages: list[dict]) -> str:
    """封装 LLM 非流式调用 (用于查询改写)"""
    response = await client.chat.completions.create(
        model=settings.LLM_MODEL,
        messages=messages,
        stream=False,
    )
    return response.choices[0].message.content