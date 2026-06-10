"""
玄照 v2.0 - LLM 客户端

调用 OpenAI 兼容 API 进行视角推理。
支持指数退避重试，提高在瞬态错误下的稳定性。
"""
import json
import logging
import time
from typing import List, Dict, Optional

import httpx

from config import LLM_API_KEY, LLM_BASE_URL, LLM_MODEL, LLM_TIMEOUT

logger = logging.getLogger(__name__)

# 可重试的 HTTP 状态码（瞬态错误）
RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}
DEFAULT_MAX_RETRIES = 3
DEFAULT_RETRY_BASE_DELAY = 2.0  # 秒，指数退避基数


class LLMClient:
    """OpenAI 兼容的 LLM 客户端，带指数退避重试"""

    def __init__(
        self,
        api_key: str = None,
        base_url: str = None,
        model: str = None,
        max_retries: int = DEFAULT_MAX_RETRIES,
        retry_base_delay: float = DEFAULT_RETRY_BASE_DELAY,
    ):
        self.api_key = api_key or LLM_API_KEY
        self.base_url = (base_url or LLM_BASE_URL).rstrip("/")
        self.model = model or LLM_MODEL
        self.timeout = LLM_TIMEOUT
        self.max_retries = max_retries
        self.retry_base_delay = retry_base_delay

    def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2000,
        model: str = None,
    ) -> str:
        """发送聊天请求，返回文本响应（带指数退避重试）"""
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

        last_error = None
        for attempt in range(self.max_retries + 1):
            try:
                with httpx.Client(timeout=self.timeout) as client:
                    resp = client.post(url, headers=headers, json=payload)

                    # 成功响应
                    if resp.status_code < 400:
                        data = resp.json()
                        return data["choices"][0]["message"]["content"]

                    # 可重试的 HTTP 错误
                    if resp.status_code in RETRYABLE_STATUS_CODES and attempt < self.max_retries:
                        delay = self.retry_base_delay * (2 ** attempt)
                        logger.warning(
                            f"LLM HTTP {resp.status_code}，"
                            f"第 {attempt + 1}/{self.max_retries} 次重试，"
                            f"等待 {delay:.1f}s..."
                        )
                        time.sleep(delay)
                        continue

                    # 不可重试或重试耗尽
                    logger.error(f"LLM HTTP error: {resp.status_code} - {resp.text[:200]}")
                    return f"[LLM 错误: {resp.status_code}]"

            except httpx.TimeoutException:
                last_error = "timeout"
                if attempt < self.max_retries:
                    delay = self.retry_base_delay * (2 ** attempt)
                    logger.warning(
                        f"LLM 超时 ({self.timeout}s)，"
                        f"第 {attempt + 1}/{self.max_retries} 次重试，"
                        f"等待 {delay:.1f}s..."
                    )
                    time.sleep(delay)
                    continue
                logger.error(f"LLM request timed out after {self.timeout}s (已重试 {self.max_retries} 次)")
                return "[LLM 超时]"

            except (httpx.ConnectError, httpx.ReadError, httpx.WriteError) as e:
                last_error = str(e)
                if attempt < self.max_retries:
                    delay = self.retry_base_delay * (2 ** attempt)
                    logger.warning(
                        f"LLM 网络错误 ({type(e).__name__})，"
                        f"第 {attempt + 1}/{self.max_retries} 次重试，"
                        f"等待 {delay:.1f}s..."
                    )
                    time.sleep(delay)
                    continue
                logger.error(f"LLM network error after {self.max_retries} retries: {e}")
                return f"[LLM 网络异常: {type(e).__name__}]"

            except Exception as e:
                logger.error(f"LLM request failed: {e}")
                return f"[LLM 异常: {type(e).__name__}]"

        # 防御性兜底
        logger.error(f"LLM 重试耗尽: {last_error}")
        return "[LLM 重试失败]"

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
