"""Tests for market news tool."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from google.genai.errors import ServerError

from tools.market_news import GetMarketNewsTool


class TestGetMarketNewsToolSchema:
    """Tests for GetMarketNewsTool schema."""

    @patch("tools.market_news.Config")
    @patch("tools.market_news.genai.Client")
    def test_schema_definition(self, mock_client, mock_config):
        """Tool schema has correct name and structure."""
        mock_config.GEMINI_API_KEY = "test_key"
        mock_config.LLM_MODEL = "gemini-2.0-flash-exp"
        mock_config.ENABLE_GROUNDING = True

        tool = GetMarketNewsTool()
        schema = tool.get_schema()

        assert schema["name"] == "get_market_news"
        assert "description" in schema
        assert "parameters" in schema
        assert schema["parameters"]["type"] == "object"
        assert schema["parameters"]["required"] == []

    @patch("tools.market_news.Config")
    @patch("tools.market_news.genai.Client")
    def test_tool_name_and_description(self, mock_client, mock_config):
        """Tool has correct name and description attributes."""
        mock_config.GEMINI_API_KEY = "test_key"
        mock_config.LLM_MODEL = "gemini-2.0-flash-exp"
        mock_config.ENABLE_GROUNDING = True

        tool = GetMarketNewsTool()

        assert tool.name == "get_market_news"
        assert "market news" in tool.description.lower()


class TestGetMarketNewsToolExecute:
    """Tests for GetMarketNewsTool.execute() method."""

    @patch("tools.market_news.Config")
    @patch("tools.market_news.genai.Client")
    @patch("tools.market_news.retry_with_backoff")
    def test_execute_success_with_grounding(self, mock_retry, mock_client_class, mock_config):
        """Successful execution returns formatted news."""
        mock_config.GEMINI_API_KEY = "test_key"
        mock_config.LLM_MODEL = "gemini-2.0-flash-exp"
        mock_config.ENABLE_GROUNDING = True

        # Mock the retry to call the function directly
        def execute_func(func, **kwargs):
            return func()

        mock_retry.side_effect = execute_func

        mock_client = Mock()
        mock_client_class.return_value = mock_client
        mock_response = Mock()
        mock_response.text = "NVDA up 5% on AI chip demand news"
        mock_client.models.generate_content.return_value = mock_response

        tool = GetMarketNewsTool()
        result = tool.execute()

        assert "TODAY'S BIGGEST NEWS" in result
        assert "NVDA up 5%" in result
        assert "Alpha Copilot" in result

    @patch("tools.market_news.Config")
    @patch("tools.market_news.genai.Client")
    @patch("tools.market_news.retry_with_backoff")
    def test_execute_grounding_disabled(self, mock_retry, mock_client_class, mock_config):
        """Works when grounding is disabled."""
        mock_config.GEMINI_API_KEY = "test_key"
        mock_config.LLM_MODEL = "gemini-2.0-flash-exp"
        mock_config.ENABLE_GROUNDING = False

        def execute_func(func, **kwargs):
            return func()

        mock_retry.side_effect = execute_func

        mock_client = Mock()
        mock_client_class.return_value = mock_client
        mock_response = Mock()
        mock_response.text = "TSLA moving on earnings report"
        mock_client.models.generate_content.return_value = mock_response

        tool = GetMarketNewsTool()
        result = tool.execute()

        assert "TODAY'S BIGGEST NEWS" in result
        assert "TSLA" in result

    @patch("tools.market_news.Config")
    @patch("tools.market_news.genai.Client")
    def test_execute_missing_api_key(self, mock_client_class, mock_config):
        """Returns error when API key is missing."""
        mock_config.GEMINI_API_KEY = None
        mock_config.LLM_MODEL = "gemini-2.0-flash-exp"
        mock_config.ENABLE_GROUNDING = True

        tool = GetMarketNewsTool()
        result = tool.execute()

        assert "ERROR" in result
        assert "GEMINI_API_KEY" in result

    @patch("tools.market_news.Config")
    @patch("tools.market_news.genai.Client")
    @patch("tools.market_news.retry_with_backoff")
    def test_execute_handles_kwargs(self, mock_retry, mock_client_class, mock_config):
        """Ignores unexpected kwargs from LLM."""
        mock_config.GEMINI_API_KEY = "test_key"
        mock_config.LLM_MODEL = "gemini-2.0-flash-exp"
        mock_config.ENABLE_GROUNDING = True

        def execute_func(func, **kwargs):
            return func()

        mock_retry.side_effect = execute_func

        mock_client = Mock()
        mock_client_class.return_value = mock_client
        mock_response = Mock()
        mock_response.text = "AMD stock moving"
        mock_client.models.generate_content.return_value = mock_response

        tool = GetMarketNewsTool()
        # LLM may pass unexpected args like query="" or other params
        result = tool.execute(query="unexpected", extra_param="also_unexpected")

        assert "TODAY'S BIGGEST NEWS" in result
        assert "AMD" in result

    @patch("tools.market_news.Config")
    @patch("tools.market_news.genai.Client")
    @patch("tools.market_news.retry_with_backoff")
    def test_execute_empty_response(self, mock_retry, mock_client_class, mock_config):
        """Handles empty response from API."""
        mock_config.GEMINI_API_KEY = "test_key"
        mock_config.LLM_MODEL = "gemini-2.0-flash-exp"
        mock_config.ENABLE_GROUNDING = True

        def execute_func(func, **kwargs):
            return func()

        mock_retry.side_effect = execute_func

        mock_client = Mock()
        mock_client_class.return_value = mock_client
        mock_response = Mock()
        mock_response.text = None  # Empty response
        mock_client.models.generate_content.return_value = mock_response

        tool = GetMarketNewsTool()

        with pytest.raises(ValueError) as exc_info:
            tool.execute()

        assert "No response from Gemini" in str(exc_info.value)

    @patch("tools.market_news.Config")
    @patch("tools.market_news.genai.Client")
    @patch("tools.market_news.retry_with_backoff")
    def test_execute_uses_retry(self, mock_retry, mock_client_class, mock_config):
        """Verifies retry_with_backoff is called with correct parameters."""
        mock_config.GEMINI_API_KEY = "test_key"
        mock_config.LLM_MODEL = "gemini-2.0-flash-exp"
        mock_config.ENABLE_GROUNDING = True

        mock_retry.return_value = "Mocked result"

        tool = GetMarketNewsTool()
        result = tool.execute()

        # Verify retry was called
        mock_retry.assert_called_once()
        call_kwargs = mock_retry.call_args[1]
        assert call_kwargs["retryable_exceptions"] == ServerError
        assert call_kwargs["operation_name"] == "Market news fetch"


class TestGetMarketNewsToolFormatResponse:
    """Tests for GetMarketNewsTool._format_response() method."""

    @patch("tools.market_news.Config")
    @patch("tools.market_news.genai.Client")
    def test_format_response_structure(self, mock_client, mock_config):
        """Format response has correct structure."""
        mock_config.GEMINI_API_KEY = "test_key"
        mock_config.LLM_MODEL = "gemini-2.0-flash-exp"
        mock_config.ENABLE_GROUNDING = True

        tool = GetMarketNewsTool()
        result = tool._format_response("Test news content")

        assert "TODAY'S BIGGEST NEWS" in result
        assert "Test news content" in result
        assert "Alpha Copilot" in result
        assert "recent posts" in result

    @patch("tools.market_news.Config")
    @patch("tools.market_news.genai.Client")
    def test_format_response_strips_whitespace(self, mock_client, mock_config):
        """Format response strips leading/trailing whitespace."""
        mock_config.GEMINI_API_KEY = "test_key"
        mock_config.LLM_MODEL = "gemini-2.0-flash-exp"
        mock_config.ENABLE_GROUNDING = True

        tool = GetMarketNewsTool()
        result = tool._format_response("  \n  News with whitespace  \n  ")

        assert "News with whitespace" in result
        # Should not have leading whitespace in the content section
        lines = result.split("\n")
        # Find the content line (after the header)
        content_found = False
        for line in lines:
            if "News with whitespace" in line:
                content_found = True
                assert line == "News with whitespace"  # No leading/trailing whitespace
        assert content_found
