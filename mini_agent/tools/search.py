from __future__ import annotations

from typing import Any

from .base import Tool, ToolResult


_MOCK_INDEX = [
    {
        "title": "Agent Runtime 基础",
        "url": "mock://agent-runtime",
        "snippet": "Agent Runtime 负责模型循环、工具调度、上下文、会话状态和执行追踪。",
        "keywords": {"agent", "runtime", "工具", "循环", "上下文"},
    },
    {
        "title": "Context 压缩策略",
        "url": "mock://context-compression",
        "snippet": "常见策略是保留最近原文，把较早消息压缩为结构化摘要，并保留关键事实与未完成任务。",
        "keywords": {"context", "压缩", "摘要", "上下文", "token"},
    },
    {
        "title": "Session 隔离",
        "url": "mock://session-isolation",
        "snippet": "用稳定 session_id 作为状态、历史、待办和 trace 的命名空间，避免窗口间串话。",
        "keywords": {"session", "会话", "隔离", "窗口", "状态"},
    },
]


class SearchTool(Tool):
    name = "search"
    description = "在内置演示知识索引中搜索内容。本工具为可重复、离线的 mock 搜索。"
    parameters = {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "搜索关键词"},
            "limit": {
                "type": "integer",
                "description": "最多返回条数，1 到 5",
            },
        },
        "required": ["query"],
        "additionalProperties": False,
    }

    def execute(self, arguments: dict[str, Any], context: dict[str, Any]) -> ToolResult:
        query = arguments["query"].strip().lower()
        limit = max(1, min(int(arguments.get("limit", 3)), 5))
        tokens = {item for item in query.replace("/", " ").split() if item}
        ranked = []
        for item in _MOCK_INDEX:
            haystack = f"{item['title']} {item['snippet']}".lower()
            score = sum(2 for token in tokens if token in item["keywords"])
            score += sum(1 for token in tokens if token in haystack)
            if score or not tokens:
                ranked.append((score, item))
        ranked.sort(key=lambda pair: pair[0], reverse=True)
        results = [
            {key: value for key, value in item.items() if key != "keywords"}
            for _, item in ranked[:limit]
        ]
        return ToolResult(ok=True, data={"query": query, "results": results, "mock": True})
