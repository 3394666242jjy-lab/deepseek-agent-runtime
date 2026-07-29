from __future__ import annotations

import json
from typing import Any

from .types import Session


class ContextManager:
    """Keeps recent turns verbatim and deterministically summarizes older turns."""

    def __init__(self, max_messages: int = 24, max_chars: int = 24_000):
        if max_messages < 6:
            raise ValueError("max_messages 至少为 6")
        self.max_messages = max_messages
        self.max_chars = max_chars

    @staticmethod
    def _size(messages: list[dict[str, Any]]) -> int:
        return sum(len(json.dumps(item, ensure_ascii=False, default=str)) for item in messages)

    def needs_compaction(self, session: Session) -> bool:
        return (
            len(session.messages) > self.max_messages
            or self._size(session.messages) > self.max_chars
        )

    @staticmethod
    def _shorten(value: str, limit: int = 280) -> str:
        clean = " ".join(value.split())
        return clean if len(clean) <= limit else clean[: limit - 1] + "…"

    def compact(self, session: Session) -> bool:
        if not self.needs_compaction(session):
            return False

        keep_count = max(6, self.max_messages // 2)
        split_at = max(1, len(session.messages) - keep_count)
        old_messages = session.messages[:split_at]
        recent_messages = session.messages[split_at:]

        facts: list[str] = []
        for message in old_messages:
            role = message.get("role", "unknown")
            if role == "assistant" and message.get("tool_calls"):
                names = [
                    call.get("function", {}).get("name", "unknown")
                    for call in message.get("tool_calls", [])
                ]
                facts.append(f"assistant 调用了工具：{', '.join(names)}")
                continue
            if role == "tool":
                name = message.get("name", "tool")
                content = self._shorten(str(message.get("content", "")), 220)
                facts.append(f"工具 {name} 返回：{content}")
                continue
            content = message.get("content")
            if content:
                facts.append(f"{role}: {self._shorten(str(content))}")

        previous = session.summary.strip()
        merged = "\n".join(facts)
        session.summary = self._shorten(
            (previous + "\n" + merged).strip(),
            max(1_200, self.max_chars // 3),
        )
        session.messages = recent_messages
        return True

    def build_messages(
        self, system_prompt: str, session: Session
    ) -> list[dict[str, Any]]:
        messages: list[dict[str, Any]] = [{"role": "system", "content": system_prompt}]
        if session.summary:
            messages.append(
                {
                    "role": "system",
                    "content": (
                        "以下是本 session 较早对话的压缩摘要。把它当作背景事实，"
                        "若与最近原文冲突，以最近原文为准：\n" + session.summary
                    ),
                }
            )
        messages.extend(session.messages)
        return messages
