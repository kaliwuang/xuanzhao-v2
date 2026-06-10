"""
玄照 v2.0 - LLM 客户端

调用 OpenAI 兼容 API 进行视角推理。
"""
import json
import logging
from typing import List, Dict, Optional

import httpx

from config import LLM_API_KEY, LLM_BASE_URL, LLM_MODEL, LLM_TIMEOUT

logger = logging.getLogger(__name__)


class LLMClient:
    """OpenAI 兼容的 LLM 客户端"""

    def __init__(self, api_key: str = None, base_url: str = None, model: str = None):
        self.api_key = api_key or LLM_API_KEY
        self.base_url = (base_url or LLM_BASE_URL).rstrip("/")
        self.model = model or LLM_MODEL
        self.timeout = LLM_TIMEOUT

    def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2000,
        model: str = None,
    ) -> str:
        """发送聊天请求，返回文本响应"""
        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": model or self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        try:
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.post(url, headers=headers, json=payload)
                resp.raise_for_status()
                data = resp.json()
                return data["choices"][0]["message"]["content"]
        except httpx.TimeoutException:
            logger.error(f"LLM request timed out after {self.timeout}s")
            return "[LLM 超时]"
        except httpx.HTTPStatusError as e:
            logger.error(f"LLM HTTP error: {e.response.status_code} - {e.response.text[:200]}")
            return f"[LLM 错误: {e.response.status_code}]"
        except Exception as e:
            logger.error(f"LLM request failed: {e}")
            return f"[LLM 异常: {type(e).__name__}]"

    def chat_json(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.3,
        max_tokens: int = 3000,
    ) -> dict:
        """发送聊天请求，尝试解析 JSON 响应"""
        raw = self.chat(messages, temperature=temperature, max_tokens=max_tokens)

        # 尝试从响应中提取 JSON
        text = raw.strip()

        # 去掉 markdown 代码块标记
        if text.startswith("```"):
            lines = text.split("\n")
            # 去掉第一行（```json 或 ```）
            lines = lines[1:]
            # 去掉最后一行的 ```
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            text = "\n".join(lines).strip()

        try:
            return json.loads(text)
        except json.JSONDecodeError:
            # 尝试找到第一个 { 和最后一个 }
            start = text.find("{")
            end = text.rfind("}")
            if start != -1 and end != -1:
                try:
                    return json.loads(text[start:end + 1])
                except json.JSONDecodeError:
                    pass

            return {"raw_response": raw, "parse_error": True}


# 全局单例
_client: Optional[LLMClient] = None


def get_llm_client() -> LLMClient:
    global _client
    if _client is None:
        _client = LLMClient()
    return _client
