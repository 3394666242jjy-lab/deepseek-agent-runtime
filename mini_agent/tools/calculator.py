from __future__ import annotations

import ast
import math
import operator
from typing import Any

from .base import Tool, ToolError, ToolResult


_BINARY = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}
_UNARY = {ast.UAdd: operator.pos, ast.USub: operator.neg}
_FUNCTIONS = {
    "abs": abs,
    "round": round,
    "sqrt": math.sqrt,
    "sin": math.sin,
    "cos": math.cos,
    "log": math.log,
}
_CONSTANTS = {"pi": math.pi, "e": math.e}


def safe_calculate(expression: str) -> int | float:
    if len(expression) > 300:
        raise ToolError("表达式过长")
    try:
        tree = ast.parse(expression, mode="eval")
    except SyntaxError as exc:
        raise ToolError("表达式语法错误") from exc

    def evaluate(node: ast.AST) -> int | float:
        if isinstance(node, ast.Expression):
            return evaluate(node.body)
        if isinstance(node, ast.Constant) and type(node.value) in {int, float}:
            return node.value
        if isinstance(node, ast.BinOp) and type(node.op) in _BINARY:
            left, right = evaluate(node.left), evaluate(node.right)
            if isinstance(node.op, ast.Pow) and abs(right) > 100:
                raise ToolError("指数过大")
            return _BINARY[type(node.op)](left, right)
        if isinstance(node, ast.UnaryOp) and type(node.op) in _UNARY:
            return _UNARY[type(node.op)](evaluate(node.operand))
        if isinstance(node, ast.Name) and node.id in _CONSTANTS:
            return _CONSTANTS[node.id]
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id in _FUNCTIONS
            and not node.keywords
        ):
            return _FUNCTIONS[node.func.id](*[evaluate(arg) for arg in node.args])
        raise ToolError("表达式包含不允许的操作")

    try:
        result = evaluate(tree)
    except ZeroDivisionError as exc:
        raise ToolError("除数不能为零") from exc
    except (OverflowError, ValueError) as exc:
        raise ToolError(f"无法计算：{exc}") from exc
    if not math.isfinite(float(result)):
        raise ToolError("计算结果不是有限数")
    return result


class CalculatorTool(Tool):
    name = "calculator"
    description = "安全计算数学表达式，支持四则运算、幂、sqrt/sin/cos/log/round/abs。"
    parameters = {
        "type": "object",
        "properties": {
            "expression": {
                "type": "string",
                "description": "要计算的数学表达式，例如 (12.5*8)+sqrt(16)",
            }
        },
        "required": ["expression"],
        "additionalProperties": False,
    }

    def execute(self, arguments: dict[str, Any], context: dict[str, Any]) -> ToolResult:
        expression = arguments["expression"]
        return ToolResult(ok=True, data={"expression": expression, "result": safe_calculate(expression)})
