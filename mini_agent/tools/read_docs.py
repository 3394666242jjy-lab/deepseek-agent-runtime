from __future__ import annotations

from pathlib import Path
from typing import Any

from .base import Tool, ToolError, ToolResult


class ReadDocsTool(Tool):
    name = "read_docs"
    description = "读取 docs 目录中的 UTF-8 文本文档，可用于查询本项目知识。"
    parameters = {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "相对 docs 目录的文件名，例如 knowledge.md",
            },
            "max_chars": {
                "type": "integer",
                "description": "最多读取字符数，默认 6000，最大 20000",
            },
        },
        "required": ["path"],
        "additionalProperties": False,
    }

    def __init__(self, docs_root: Path):
        self.docs_root = docs_root.resolve()

    def execute(self, arguments: dict[str, Any], context: dict[str, Any]) -> ToolResult:
        requested = arguments["path"].strip()
        target = (self.docs_root / requested).resolve()
        try:
            target.relative_to(self.docs_root)
        except ValueError as exc:
            raise ToolError("只允许读取 docs 目录内的文件") from exc
        if not target.is_file():
            raise ToolError(f"文档不存在：{requested}")
        if target.suffix.lower() not in {".md", ".txt", ".json"}:
            raise ToolError("只支持 .md、.txt、.json 文档")
        limit = max(1, min(int(arguments.get("max_chars", 6000)), 20_000))
        content = target.read_text(encoding="utf-8")
        return ToolResult(
            ok=True,
            data={
                "path": requested,
                "content": content[:limit],
                "truncated": len(content) > limit,
            },
        )
