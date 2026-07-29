from pathlib import Path

from .calculator import CalculatorTool
from .read_docs import ReadDocsTool
from .registry import ToolRegistry
from .search import SearchTool
from .todo import TodoTool
from .weather import WeatherTool


def build_default_registry(docs_root: Path = Path("docs")) -> ToolRegistry:
    registry = ToolRegistry()
    registry.register(CalculatorTool())
    registry.register(SearchTool())
    registry.register(TodoTool())
    registry.register(WeatherTool())
    registry.register(ReadDocsTool(docs_root))
    return registry
