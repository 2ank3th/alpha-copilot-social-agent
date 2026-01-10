"""Tests for agent tools."""

import pytest
from tools.base import BaseTool
from tools.registry import ToolRegistry
from tools.write import WritePostTool


class TestToolRegistry:
    """Tests for ToolRegistry class."""

    def test_register_tool(self):
        """Test that tools can be registered."""
        registry = ToolRegistry()
        tool = WritePostTool()
        registry.register(tool)

        assert len(registry) == 1
        assert "write_post" in registry.list_tools()

    def test_get_tool(self):
        """Test that registered tools can be retrieved."""
        registry = ToolRegistry()
        tool = WritePostTool()
        registry.register(tool)

        retrieved = registry.get("write_post")
        assert retrieved is tool

    def test_get_nonexistent_tool_raises(self):
        """Test that getting nonexistent tool raises ValueError."""
        registry = ToolRegistry()

        with pytest.raises(ValueError, match="not found"):
            registry.get("nonexistent")

    def test_get_schemas(self):
        """Test that schemas are returned for all tools."""
        registry = ToolRegistry()
        registry.register(WritePostTool())

        schemas = registry.get_schemas()
        assert len(schemas) == 1
        assert schemas[0]["name"] == "write_post"


class TestWritePostTool:
    """Tests for WritePostTool class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.tool = WritePostTool()

    def test_tool_has_name_and_description(self):
        """Test that tool has required attributes."""
        assert self.tool.name == "write_post"
        assert len(self.tool.description) > 0

    def test_get_schema_returns_valid_schema(self):
        """Test that get_schema returns a valid schema."""
        schema = self.tool.get_schema()

        assert "name" in schema
        assert "description" in schema
        assert "parameters" in schema
        assert schema["parameters"]["type"] == "object"

    def test_execute_validates_length_twitter(self):
        """Test that Twitter posts are validated for 280 chars."""
        long_post = "x" * 300
        result = self.tool.execute(long_post, "twitter")

        assert "ERROR" in result
        assert "too long" in result

    def test_execute_validates_length_threads(self):
        """Test that Threads posts are validated for 500 chars."""
        long_post = "x" * 600
        result = self.tool.execute(long_post, "threads")

        assert "ERROR" in result
        assert "too long" in result

    def test_execute_validates_minimum_length(self):
        """Test that posts must be at least 50 chars."""
        short_post = "Too short"
        result = self.tool.execute(short_post, "twitter")

        assert "ERROR" in result
        assert "too short" in result

    def test_execute_success_returns_post_ready(self):
        """Test that valid posts return POST_READY."""
        valid_post = "$NVDA up 5% today on AI demand! Sell the $950 call for $12 premium. #NFA"
        result = self.tool.execute(valid_post, "twitter")

        assert "POST_READY" in result
        assert "POST TEXT:" in result

    def test_execute_warns_no_ticker(self):
        """Test that posts without ticker get a warning."""
        no_ticker_post = "Stock is up 5% today! Great opportunity for options traders. Check it out now!"
        result = self.tool.execute(no_ticker_post, "twitter")

        assert "WARNING" in result
        assert "ticker" in result.lower()

    def test_execute_warns_no_numbers(self):
        """Test that posts without numbers get a warning."""
        no_numbers_post = "$NVDA is looking strong today with great momentum and bullish sentiment!"
        result = self.tool.execute(no_numbers_post, "twitter")

        assert "WARNING" in result
        assert "numbers" in result.lower()
