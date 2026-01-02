"""Base class for all tools."""

from abc import ABC, abstractmethod
from typing import Any, Dict


class BaseTool(ABC):
    """Abstract base class for agent tools."""

    name: str
    description: str

    @abstractmethod
    def get_schema(self) -> Dict[str, Any]:
        """
        Return the JSON schema for tool parameters.

        Returns:
            Dict with 'name', 'description', and 'parameters' (JSON Schema)
        """
        pass

    @abstractmethod
    def execute(self, **kwargs) -> str:
        """
        Execute the tool with given parameters.

        Args:
            **kwargs: Tool-specific parameters

        Returns:
            String result to be added to agent context
        """
        pass

    def __repr__(self) -> str:
        return f"<Tool: {self.name}>"
