from __future__ import annotations

import hashlib
from datetime import date
from typing import Any

from .base import Tool, ToolResult


_CONDITIONS = ["晴", "多云", "小雨", "阴", "阵雨"]


class WeatherTool(Tool):
    name = "weather"
    description = "查询城市天气。当前为确定性的 mock 数据，适合离线演示和测试。"
    parameters = {
        "type": "object",
        "properties": {
            "city": {"type": "string", "description": "城市，例如 上海"},
            "date": {
                "type": "string",
                "description": "ISO 日期 YYYY-MM-DD；默认今天",
            },
        },
        "required": ["city"],
        "additionalProperties": False,
    }

    def execute(self, arguments: dict[str, Any], context: dict[str, Any]) -> ToolResult:
        city = arguments["city"].strip()
        day = arguments.get("date") or date.today().isoformat()
        digest = hashlib.sha256(f"{city}:{day}".encode()).digest()
        low = 8 + digest[0] % 18
        high = low + 4 + digest[1] % 8
        condition = _CONDITIONS[digest[2] % len(_CONDITIONS)]
        return ToolResult(
            ok=True,
            data={
                "city": city,
                "date": day,
                "condition": condition,
                "temperature_c": {"low": low, "high": high},
                "mock": True,
            },
        )
