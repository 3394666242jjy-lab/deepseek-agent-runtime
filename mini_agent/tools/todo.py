from __future__ import annotations

from typing import Any
from uuid import uuid4

from .base import Tool, ToolError, ToolResult
from ..tracing import utc_now


class TodoTool(Tool):
    name = "todo"
    description = "管理当前 session 独立的待办；支持 add、list、complete、delete。"
    parameters = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["add", "list", "complete", "delete"],
                "description": "待办操作",
            },
            "text": {"type": "string", "description": "add 时的待办内容"},
            "todo_id": {
                "type": "string",
                "description": "complete/delete 时的待办 ID；可用 list 查询",
            },
        },
        "required": ["action"],
        "additionalProperties": False,
    }

    def execute(self, arguments: dict[str, Any], context: dict[str, Any]) -> ToolResult:
        state = context["session"].state
        todos = state.setdefault("todos", [])
        action = arguments["action"]
        if action == "list":
            return ToolResult(ok=True, data={"todos": todos})
        if action == "add":
            text = arguments.get("text", "").strip()
            if not text:
                raise ToolError("add 操作必须提供非空 text")
            item = {
                "id": uuid4().hex[:8],
                "text": text,
                "done": False,
                "created_at": utc_now(),
            }
            todos.append(item)
            return ToolResult(ok=True, data={"todo": item, "count": len(todos)})

        todo_id = arguments.get("todo_id", "").strip()
        if not todo_id:
            raise ToolError(f"{action} 操作必须提供 todo_id")
        item = next((todo for todo in todos if todo["id"] == todo_id), None)
        if item is None:
            raise ToolError(f"找不到待办：{todo_id}")
        if action == "complete":
            item["done"] = True
            item["completed_at"] = utc_now()
            return ToolResult(ok=True, data={"todo": item})
        todos.remove(item)
        return ToolResult(ok=True, data={"deleted": item})
