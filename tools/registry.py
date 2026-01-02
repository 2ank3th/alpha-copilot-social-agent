"""Tool registry for managing available tools."""

from typing import Dict, List, Any
from .base import BaseTool


class ToolRegistry:
    """Registry for managing and executing tools."""

    def __init__(self):
        self._tools: Dict[str, BaseTool] = {}

    def register(self, tool: BaseTool) -> None:
        """Register a tool."""
        self._tools[tool.name] = tool

    def get(self, name: str) -> BaseTool:
        """Get a tool by name."""
        if name not in self._tools:
            raise ValueError(f"Tool '{name}' not found. Available: {list(self._tools.keys())}")
        return self._tools[name]

    def execute(self, name: str, **kwargs) -> str:
        """Execute a tool by name with given arguments."""
        tool = self.get(name)
        return tool.execute(**kwargs)

    def get_schemas(self) -> List[Dict[str, Any]]:
        """Get JSON schemas for all registered tools."""
        return [tool.get_schema() for tool in self._tools.values()]

    def list_tools(self) -> List[str]:
        """List all registered tool names."""
        return list(self._tools.keys())

    def __len__(self) -> int:
        return len(self._tools)

    def __repr__(self) -> str:
        return f"<ToolRegistry: {self.list_tools()}>"
