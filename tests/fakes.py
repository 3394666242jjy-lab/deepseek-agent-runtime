from __future__ import annotations

from collections import deque
from typing import Any

from mini_agent.types import ModelDecision


class FakeLLM:
    def __init__(self, decisions: list[ModelDecision]):
        self.decisions = deque(decisions)
        self.calls: list[dict[str, Any]] = []

    def chat(
        self, messages: list[dict[str, Any]], tools: list[dict[str, Any]]
    ) -> ModelDecision:
        self.calls.append({"messages": messages, "tools": tools})
        if not self.decisions:
            raise AssertionError("FakeLLM 没有剩余响应")
        return self.decisions.popleft()
