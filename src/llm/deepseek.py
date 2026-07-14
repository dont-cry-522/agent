"""
DeepSeekLLM — DeepSeek API 调用模块

职责：
  - 封装对 DeepSeek Chat Completions API 的 HTTP 调用
  - 所有 HTTP 请求逻辑都集中在此模块内

独立出来的原因 (为什么不直接查 FAISS)：
  - LLM 的职责是调用 API 生成文本，不知道什么是 FAISS
  - 如果把 FAISS 查询写进 LLM，就耦合了检索和生成
  - 替换任何一个都需要改动对方，违反单一职责原则
"""

from __future__ import annotations

import httpx

from src.config import settings


class DeepSeekLLM:
    """DeepSeek Chat Completions 客户端

    API 文档: https://api-docs.deepseek.com/zh-cn/
    """

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str = "deepseek-chat",
    ):
        self.api_key = api_key or settings.deepseek_api_key
        self.base_url = (base_url or settings.deepseek_base_url).rstrip("/")
        self.model = model
        self._client = httpx.Client(
            base_url=self.base_url,
            timeout=60.0,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
        )

    def chat(
        self,
        system_prompt: str,
        user_message: str,
        *,
        temperature: float = 0.7,
        max_tokens: int = 1024,
    ) -> str:
        """发送 Chat 请求，返回 LLM 生成的文本"""

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False,
        }

        response = self._client.post("/v1/chat/completions", json=payload)
        response.raise_for_status()
        data = response.json()

        return data["choices"][0]["message"]["content"]
