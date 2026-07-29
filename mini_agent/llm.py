from __future__ import annotations

import json
import re
import time
import urllib.error
import urllib.request
from typing import Any, Protocol
from uuid import uuid4

from .types import ModelDecision, ToolCall


class LLMError(RuntimeError):
    pass


class LLMClient(Protocol):
    def chat(
        self, messages: list[dict[str, Any]], tools: list[dict[str, Any]]
    ) -> ModelDecision: ...


_THINK_RE = re.compile(r"<think>(.*?)</think>", re.DOTALL | re.IGNORECASE)
_FENCE_RE = re.compile(r"```(?:json)?\s*(\{.*?\})\s*```", re.DOTALL | re.IGNORECASE)


def _parse_arguments(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if not isinstance(value, str) or not value.strip():
        return {}
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError as exc:
        raise LLMError(f"模型返回的工具参数不是合法 JSON：{value[:200]}") from exc
    if not isinstance(parsed, dict):
        raise LLMError("模型返回的工具参数必须是 JSON 对象")
    return parsed


def _extract_json_object(content: str) -> dict[str, Any] | None:
    candidates = [match.group(1) for match in _FENCE_RE.finditer(content)]
    stripped = content.strip()
    if stripped.startswith("{") and stripped.endswith("}"):
        candidates.append(stripped)
    for candidate in candidates:
        try:
            value = json.loads(candidate)
            if isinstance(value, dict):
                return value
        except json.JSONDecodeError:
            continue
    return None


def parse_model_message(message: dict[str, Any]) -> ModelDecision:
    """Parse native function calls plus a documented JSON fallback protocol."""
    content = message.get("content") or ""
    reasoning = message.get("reasoning_content") or ""
    think_match = _THINK_RE.search(content)
    if think_match:
        reasoning = reasoning or think_match.group(1).strip()
        content = _THINK_RE.sub("", content).strip()

    tool_calls: list[ToolCall] = []
    for call in message.get("tool_calls") or []:
        function = call.get("function") or {}
        name = function.get("name")
        if not name:
            continue
        tool_calls.append(
            ToolCall(
                id=call.get("id") or f"call_{uuid4().hex}",
                name=name,
                arguments=_parse_arguments(function.get("arguments")),
            )
        )

    # Some compatible endpoints do not implement native function calling.
    # Accept {"tool_call": {"name": "...", "arguments": {...}}} as fallback.
    if not tool_calls and content:
        fallback = _extract_json_object(content)
        if fallback and isinstance(fallback.get("tool_call"), dict):
            call = fallback["tool_call"]
            if call.get("name"):
                tool_calls.append(
                    ToolCall(
                        id=f"call_{uuid4().hex}",
                        name=str(call["name"]),
                        arguments=_parse_arguments(call.get("arguments", {})),
                    )
                )
                reasoning = reasoning or str(fallback.get("thought", ""))
                content = ""
        elif fallback and "final" in fallback:
            reasoning = reasoning or str(fallback.get("thought", ""))
            content = str(fallback["final"])

    raw_message: dict[str, Any] = {"role": "assistant", "content": content or None}
    if message.get("tool_calls"):
        raw_message["tool_calls"] = message["tool_calls"]
    return ModelDecision(
        content=content,
        reasoning=reasoning,
        tool_calls=tool_calls,
        raw_message=raw_message,
    )


class DeepSeekClient:
    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.deepseek.com",
        model: str = "deepseek-v4-flash",
        timeout: int = 60,
        max_retries: int = 2,
    ):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout
        self.max_retries = max_retries

    def _request(self, payload: dict[str, Any]) -> dict[str, Any]:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        request = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=body,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            method="POST",
        )
        last_error: Exception | None = None
        for attempt in range(self.max_retries + 1):
            try:
                with urllib.request.urlopen(request, timeout=self.timeout) as response:
                    data = json.loads(response.read().decode("utf-8"))
                if not isinstance(data, dict):
                    raise LLMError("API 返回格式不是 JSON 对象")
                return data
            except urllib.error.HTTPError as exc:
                detail = exc.read().decode("utf-8", errors="replace")[:1000]
                if exc.code not in {408, 429, 500, 502, 503, 504}:
                    raise LLMError(f"DeepSeek API HTTP {exc.code}: {detail}") from exc
                last_error = LLMError(f"DeepSeek API HTTP {exc.code}: {detail}")
            except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
                last_error = exc
            if attempt < self.max_retries:
                time.sleep(0.5 * (2**attempt))
        raise LLMError(f"DeepSeek API 请求失败：{last_error}") from last_error

    def chat(
        self, messages: list[dict[str, Any]], tools: list[dict[str, Any]]
    ) -> ModelDecision:
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.2,
            "stream": False,
        }
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"
        data = self._request(payload)
        choices = data.get("choices") or []
        if not choices or not isinstance(choices[0].get("message"), dict):
            raise LLMError(f"API 响应缺少 choices[0].message：{str(data)[:500]}")
        return parse_model_message(choices[0]["message"])
