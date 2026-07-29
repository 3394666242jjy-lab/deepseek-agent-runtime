from __future__ import annotations

from typing import Any

from .base import Tool, ToolError, ToolResult


_JSON_TYPES: dict[str, tuple[type, ...]] = {
    "string": (str,),
    "number": (int, float),
    "integer": (int,),
    "boolean": (bool,),
    "array": (list,),
    "object": (dict,),
}


class ToolRegistry:
    def __init__(self):
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> Tool:
        if not tool.name or tool.name in self._tools:
            raise ValueError(f"工具名为空或重复：{tool.name!r}")
        self._tools[tool.name] = tool
        return tool

    def schemas(self) -> list[dict[str, Any]]:
        return [tool.schema() for tool in self._tools.values()]

    def names(self) -> list[str]:
        return list(self._tools)

    def get(self, name: str) -> Tool:
        try:
            return self._tools[name]
        except KeyError as exc:
            raise ToolError(f"未知工具：{name}") from exc

    @staticmethod
    def _validate(schema: dict[str, Any], arguments: dict[str, Any]) -> None:
        if not isinstance(arguments, dict):
            raise ToolError("工具参数必须是 JSON 对象")
        required = schema.get("required", [])
        missing = [key for key in required if key not in arguments]
        if missing:
            raise ToolError(f"缺少必填参数：{', '.join(missing)}")
        properties = schema.get("properties", {})
        extra = [key for key in arguments if key not in properties]
        if extra and schema.get("additionalProperties") is False:
            raise ToolError(f"包含未声明参数：{', '.join(extra)}")
        for key, value in arguments.items():
            spec = properties.get(key)
            if not spec or value is None:
                continue
            expected = _JSON_TYPES.get(spec.get("type"))
            if expected and (
                not isinstance(value, expected)
                or (spec.get("type") in {"number", "integer"} and isinstance(value, bool))
            ):
                raise ToolError(f"参数 {key} 类型错误，应为 {spec['type']}")
            if "enum" in spec and value not in spec["enum"]:
                raise ToolError(f"参数 {key} 必须为：{spec['enum']}")

    def execute(
        self, name: str, arguments: dict[str, Any], context: dict[str, Any]
    ) -> ToolResult:
        tool = self.get(name)
        self._validate(tool.parameters, arguments)
        return tool.execute(arguments, context)
