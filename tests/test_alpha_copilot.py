"""Tests for Alpha Copilot tool."""

import pytest
from unittest.mock import Mock, patch, MagicMock
import httpx


class TestQueryAlphaCopilotToolInit:
    """Tests for QueryAlphaCopilotTool initialization."""

    @patch("tools.alpha_copilot.SupabaseAuth")
    @patch("tools.alpha_copilot.Config")
    def test_init_with_supabase_auth(self, mock_config, mock_supabase_auth):
        """Test initialization with Supabase authentication."""
        mock_config.ALPHA_COPILOT_API_URL = "https://api.test.com"
        mock_config.ALPHA_COPILOT_API_KEY = None
        mock_config.validate_supabase.return_value = True

        from tools.alpha_copilot import QueryAlphaCopilotTool
        tool = QueryAlphaCopilotTool()

        assert tool._supabase_auth is not None
        mock_supabase_auth.assert_called_once()

    @patch("tools.alpha_copilot.SupabaseAuth")
    @patch("tools.alpha_copilot.Config")
    def test_init_with_api_key(self, mock_config, mock_supabase_auth):
        """Test initialization with static API key."""
        mock_config.ALPHA_COPILOT_API_URL = "https://api.test.com"
        mock_config.ALPHA_COPILOT_API_KEY = "test_api_key"
        mock_config.validate_supabase.return_value = False

        from tools.alpha_copilot import QueryAlphaCopilotTool
        tool = QueryAlphaCopilotTool()

        assert tool._supabase_auth is None
        assert tool.api_key == "test_api_key"

    @patch("tools.alpha_copilot.Config")
    def test_init_without_auth(self, mock_config):
        """Test initialization without any authentication."""
        mock_config.ALPHA_COPILOT_API_URL = "https://api.test.com"
        mock_config.ALPHA_COPILOT_API_KEY = None
        mock_config.validate_supabase.return_value = False

        from tools.alpha_copilot import QueryAlphaCopilotTool
        tool = QueryAlphaCopilotTool()

        assert tool._supabase_auth is None
        assert tool.api_key is None


class TestQueryAlphaCopilotToolSchema:
    """Tests for QueryAlphaCopilotTool schema."""

    @patch("tools.alpha_copilot.Config")
    def test_schema_definition(self, mock_config):
        """Test tool schema is correctly defined."""
        mock_config.ALPHA_COPILOT_API_URL = "https://api.test.com"
        mock_config.ALPHA_COPILOT_API_KEY = "test_key"
        mock_config.validate_supabase.return_value = False

        from tools.alpha_copilot import QueryAlphaCopilotTool
        tool = QueryAlphaCopilotTool()
        schema = tool.get_schema()

        assert schema["name"] == "query_alpha_copilot"
        assert "query" in schema["parameters"]["properties"]
        assert "query" in schema["parameters"]["required"]


class TestQueryAlphaCopilotToolExecute:
    """Tests for QueryAlphaCopilotTool.execute() method."""

    @patch("tools.alpha_copilot.Config")
    def test_execute_no_auth_configured(self, mock_config):
        """Test execute fails when no auth is configured."""
        mock_config.ALPHA_COPILOT_API_URL = "https://api.test.com"
        mock_config.ALPHA_COPILOT_API_KEY = None
        mock_config.validate_supabase.return_value = False

        from tools.alpha_copilot import QueryAlphaCopilotTool
        tool = QueryAlphaCopilotTool()
        result = tool.execute("Find bullish plays for NVDA")

        assert "ERROR" in result
        assert "No authentication" in result

    @patch("tools.alpha_copilot.SupabaseAuth")
    @patch("tools.alpha_copilot.Config")
    def test_execute_supabase_auth_failure(self, mock_config, mock_supabase_auth):
        """Test execute fails when Supabase auth fails."""
        mock_config.ALPHA_COPILOT_API_URL = "https://api.test.com"
        mock_config.ALPHA_COPILOT_API_KEY = None
        mock_config.validate_supabase.return_value = True

        mock_auth = Mock()
        mock_auth.get_access_token.return_value = None
        mock_supabase_auth.return_value = mock_auth

        from tools.alpha_copilot import QueryAlphaCopilotTool
        tool = QueryAlphaCopilotTool()
        result = tool.execute("Find bullish plays")

        assert "ERROR" in result
        assert "Failed to authenticate" in result

    @patch("tools.alpha_copilot.Config")
    def test_execute_success_with_recommendations(self, mock_config):
        """Test successful execution with recommendations."""
        mock_config.ALPHA_COPILOT_API_URL = "https://api.test.com"
        mock_config.ALPHA_COPILOT_API_KEY = "test_key"
        mock_config.validate_supabase.return_value = False

        from tools.alpha_copilot import QueryAlphaCopilotTool
        tool = QueryAlphaCopilotTool()

        mock_response = Mock()
        mock_response.json.return_value = {
            "status": "success",
            "analysis": {
                "market_overview": "Bullish market",
                "recommendations": [
                    {
                        "symbol": "NVDA",
                        "strategy": "Covered Call",
                        "strike": 950,
                        "premium": 12.50,
                        "probability_of_profit": 75,
                        "expiration": "Jan 17",
                        "delta": 0.30,
                        "rationale": "Strong momentum on AI demand"
                    }
                ]
            }
        }
        mock_response.raise_for_status = Mock()
        tool._client = Mock()
        tool._client.post.return_value = mock_response

        result = tool.execute("Find covered calls for NVDA")

        assert "RECOMMENDATION 1" in result
        assert "NVDA" in result
        assert "Covered Call" in result
        assert "Strike: $950" in result

    @patch("tools.alpha_copilot.Config")
    def test_execute_needs_clarification(self, mock_config):
        """Test execution when clarification is needed."""
        mock_config.ALPHA_COPILOT_API_URL = "https://api.test.com"
        mock_config.ALPHA_COPILOT_API_KEY = "test_key"
        mock_config.validate_supabase.return_value = False

        from tools.alpha_copilot import QueryAlphaCopilotTool
        tool = QueryAlphaCopilotTool()

        mock_response = Mock()
        mock_response.json.return_value = {
            "status": "needs_clarification",
            "message": "Please specify the ticker symbol"
        }
        mock_response.raise_for_status = Mock()
        tool._client = Mock()
        tool._client.post.return_value = mock_response

        result = tool.execute("Find options")

        assert "CLARIFICATION_NEEDED" in result
        assert "ticker symbol" in result

    @patch("tools.alpha_copilot.Config")
    def test_execute_no_recommendations(self, mock_config):
        """Test execution when no recommendations returned."""
        mock_config.ALPHA_COPILOT_API_URL = "https://api.test.com"
        mock_config.ALPHA_COPILOT_API_KEY = "test_key"
        mock_config.validate_supabase.return_value = False

        from tools.alpha_copilot import QueryAlphaCopilotTool
        tool = QueryAlphaCopilotTool()

        mock_response = Mock()
        mock_response.json.return_value = {
            "status": "success",
            "analysis": {
                "market_overview": "No good setups",
                "recommendations": []
            }
        }
        mock_response.raise_for_status = Mock()
        tool._client = Mock()
        tool._client.post.return_value = mock_response

        result = tool.execute("Find options for XYZ")

        assert "NO_RECOMMENDATIONS" in result

    @patch("tools.alpha_copilot.Config")
    def test_execute_api_error_status(self, mock_config):
        """Test execution when API returns error status."""
        mock_config.ALPHA_COPILOT_API_URL = "https://api.test.com"
        mock_config.ALPHA_COPILOT_API_KEY = "test_key"
        mock_config.validate_supabase.return_value = False

        from tools.alpha_copilot import QueryAlphaCopilotTool
        tool = QueryAlphaCopilotTool()

        mock_response = Mock()
        mock_response.json.return_value = {
            "status": "error",
            "error_message": "Invalid ticker symbol"
        }
        mock_response.raise_for_status = Mock()
        tool._client = Mock()
        tool._client.post.return_value = mock_response

        result = tool.execute("Find options for INVALID")

        assert "ERROR" in result
        assert "Invalid ticker" in result

    @patch("tools.alpha_copilot.Config")
    def test_execute_timeout(self, mock_config):
        """Test execution handles timeout."""
        mock_config.ALPHA_COPILOT_API_URL = "https://api.test.com"
        mock_config.ALPHA_COPILOT_API_KEY = "test_key"
        mock_config.validate_supabase.return_value = False

        from tools.alpha_copilot import QueryAlphaCopilotTool
        tool = QueryAlphaCopilotTool()
        tool._client = Mock()
        tool._client.post.side_effect = httpx.TimeoutException("Request timed out")

        result = tool.execute("Find options")

        assert "ERROR" in result
        assert "timed out" in result.lower()

    @patch("tools.alpha_copilot.Config")
    def test_execute_http_401_with_api_key(self, mock_config):
        """Test execution handles 401 with API key."""
        mock_config.ALPHA_COPILOT_API_URL = "https://api.test.com"
        mock_config.ALPHA_COPILOT_API_KEY = "test_key"
        mock_config.validate_supabase.return_value = False

        from tools.alpha_copilot import QueryAlphaCopilotTool
        tool = QueryAlphaCopilotTool()
        tool._client = Mock()

        mock_response = Mock()
        mock_response.status_code = 401
        error = httpx.HTTPStatusError("Unauthorized", request=Mock(), response=mock_response)
        tool._client.post.side_effect = error

        result = tool.execute("Find options")

        assert "ERROR" in result
        assert "401" in result

    @patch("tools.alpha_copilot.SupabaseAuth")
    @patch("tools.alpha_copilot.Config")
    def test_execute_http_401_with_token_refresh(self, mock_config, mock_supabase_auth):
        """Test execution retries with refreshed token on 401."""
        mock_config.ALPHA_COPILOT_API_URL = "https://api.test.com"
        mock_config.ALPHA_COPILOT_API_KEY = None
        mock_config.validate_supabase.return_value = True

        mock_auth = Mock()
        mock_auth.get_access_token.side_effect = ["old_token", "new_token"]
        mock_auth.refresh.return_value = (True, "Token refreshed")
        mock_supabase_auth.return_value = mock_auth

        from tools.alpha_copilot import QueryAlphaCopilotTool
        tool = QueryAlphaCopilotTool()

        # First call fails with 401
        mock_response_401 = Mock()
        mock_response_401.status_code = 401
        error = httpx.HTTPStatusError("Unauthorized", request=Mock(), response=mock_response_401)

        # Second call succeeds
        mock_response_success = Mock()
        mock_response_success.json.return_value = {
            "status": "success",
            "analysis": {
                "market_overview": "Test",
                "recommendations": [{"symbol": "NVDA", "strategy": "Call", "rationale": "Good"}]
            }
        }
        mock_response_success.raise_for_status = Mock()

        tool._client = Mock()
        tool._client.post.side_effect = [error, mock_response_success]

        result = tool.execute("Find options")

        assert "RECOMMENDATION" in result
        mock_auth.refresh.assert_called_once()

    @patch("tools.alpha_copilot.SupabaseAuth")
    @patch("tools.alpha_copilot.Config")
    def test_execute_http_401_refresh_fails(self, mock_config, mock_supabase_auth):
        """Test execution fails when token refresh fails."""
        mock_config.ALPHA_COPILOT_API_URL = "https://api.test.com"
        mock_config.ALPHA_COPILOT_API_KEY = None
        mock_config.validate_supabase.return_value = True

        mock_auth = Mock()
        mock_auth.get_access_token.return_value = "token"
        mock_auth.refresh.return_value = (False, "Refresh failed")
        mock_supabase_auth.return_value = mock_auth

        from tools.alpha_copilot import QueryAlphaCopilotTool
        tool = QueryAlphaCopilotTool()

        mock_response = Mock()
        mock_response.status_code = 401
        error = httpx.HTTPStatusError("Unauthorized", request=Mock(), response=mock_response)
        tool._client = Mock()
        tool._client.post.side_effect = error

        result = tool.execute("Find options")

        assert "ERROR" in result
        assert "Token refresh failed" in result

    @patch("tools.alpha_copilot.Config")
    def test_execute_http_403(self, mock_config):
        """Test execution handles 403 forbidden."""
        mock_config.ALPHA_COPILOT_API_URL = "https://api.test.com"
        mock_config.ALPHA_COPILOT_API_KEY = "test_key"
        mock_config.validate_supabase.return_value = False

        from tools.alpha_copilot import QueryAlphaCopilotTool
        tool = QueryAlphaCopilotTool()

        mock_response = Mock()
        mock_response.status_code = 403
        error = httpx.HTTPStatusError("Forbidden", request=Mock(), response=mock_response)
        tool._client = Mock()
        tool._client.post.side_effect = error

        result = tool.execute("Find options")

        assert "ERROR" in result
        assert "403" in result
        assert "Access forbidden" in result

    @patch("tools.alpha_copilot.Config")
    def test_execute_http_500(self, mock_config):
        """Test execution handles 500 server error."""
        mock_config.ALPHA_COPILOT_API_URL = "https://api.test.com"
        mock_config.ALPHA_COPILOT_API_KEY = "test_key"
        mock_config.validate_supabase.return_value = False

        from tools.alpha_copilot import QueryAlphaCopilotTool
        tool = QueryAlphaCopilotTool()

        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        error = httpx.HTTPStatusError("Server Error", request=Mock(), response=mock_response)
        tool._client = Mock()
        tool._client.post.side_effect = error

        result = tool.execute("Find options")

        assert "ERROR" in result
        assert "500" in result

    @patch("tools.alpha_copilot.Config")
    def test_execute_http_error(self, mock_config):
        """Test execution handles general HTTP errors."""
        mock_config.ALPHA_COPILOT_API_URL = "https://api.test.com"
        mock_config.ALPHA_COPILOT_API_KEY = "test_key"
        mock_config.validate_supabase.return_value = False

        from tools.alpha_copilot import QueryAlphaCopilotTool
        tool = QueryAlphaCopilotTool()
        tool._client = Mock()
        tool._client.post.side_effect = httpx.HTTPError("Connection failed")

        result = tool.execute("Find options")

        assert "ERROR" in result
        assert "HTTP error" in result

    @patch("tools.alpha_copilot.Config")
    def test_execute_general_exception(self, mock_config):
        """Test execution handles general exceptions."""
        mock_config.ALPHA_COPILOT_API_URL = "https://api.test.com"
        mock_config.ALPHA_COPILOT_API_KEY = "test_key"
        mock_config.validate_supabase.return_value = False

        from tools.alpha_copilot import QueryAlphaCopilotTool
        tool = QueryAlphaCopilotTool()
        tool._client = Mock()
        tool._client.post.side_effect = Exception("Unexpected error")

        result = tool.execute("Find options")

        assert "ERROR" in result
        assert "Unexpected error" in result


class TestQueryAlphaCopilotToolGetAuthToken:
    """Tests for _get_auth_token method."""

    @patch("tools.alpha_copilot.SupabaseAuth")
    @patch("tools.alpha_copilot.Config")
    def test_get_auth_token_from_supabase(self, mock_config, mock_supabase_auth):
        """Test getting token from Supabase auth."""
        mock_config.ALPHA_COPILOT_API_URL = "https://api.test.com"
        mock_config.ALPHA_COPILOT_API_KEY = "fallback_key"
        mock_config.validate_supabase.return_value = True

        mock_auth = Mock()
        mock_auth.get_access_token.return_value = "supabase_token"
        mock_supabase_auth.return_value = mock_auth

        from tools.alpha_copilot import QueryAlphaCopilotTool
        tool = QueryAlphaCopilotTool()
        token = tool._get_auth_token()

        assert token == "supabase_token"

    @patch("tools.alpha_copilot.Config")
    def test_get_auth_token_from_api_key(self, mock_config):
        """Test getting token from static API key."""
        mock_config.ALPHA_COPILOT_API_URL = "https://api.test.com"
        mock_config.ALPHA_COPILOT_API_KEY = "static_api_key"
        mock_config.validate_supabase.return_value = False

        from tools.alpha_copilot import QueryAlphaCopilotTool
        tool = QueryAlphaCopilotTool()
        token = tool._get_auth_token()

        assert token == "static_api_key"

    @patch("tools.alpha_copilot.Config")
    def test_get_auth_token_returns_none(self, mock_config):
        """Test getting token returns None when no auth configured."""
        mock_config.ALPHA_COPILOT_API_URL = "https://api.test.com"
        mock_config.ALPHA_COPILOT_API_KEY = None
        mock_config.validate_supabase.return_value = False

        from tools.alpha_copilot import QueryAlphaCopilotTool
        tool = QueryAlphaCopilotTool()
        token = tool._get_auth_token()

        assert token is None


class TestQueryAlphaCopilotToolCleanup:
    """Tests for tool cleanup."""

    @patch("tools.alpha_copilot.Config")
    def test_del_closes_client(self, mock_config):
        """Test __del__ closes HTTP client."""
        mock_config.ALPHA_COPILOT_API_URL = "https://api.test.com"
        mock_config.ALPHA_COPILOT_API_KEY = "key"
        mock_config.validate_supabase.return_value = False

        from tools.alpha_copilot import QueryAlphaCopilotTool
        tool = QueryAlphaCopilotTool()
        mock_client = Mock()
        tool._client = mock_client

        del tool

        mock_client.close.assert_called_once()


class TestResponseFormatting:
    """Tests for response formatting."""

    @patch("tools.alpha_copilot.Config")
    def test_formats_multiple_recommendations(self, mock_config):
        """Test formatting of multiple recommendations."""
        mock_config.ALPHA_COPILOT_API_URL = "https://api.test.com"
        mock_config.ALPHA_COPILOT_API_KEY = "test_key"
        mock_config.validate_supabase.return_value = False

        from tools.alpha_copilot import QueryAlphaCopilotTool
        tool = QueryAlphaCopilotTool()

        mock_response = Mock()
        mock_response.json.return_value = {
            "status": "success",
            "analysis": {
                "market_overview": "Mixed market",
                "recommendations": [
                    {"symbol": "NVDA", "strategy": "Covered Call", "rationale": "AI momentum"},
                    {"symbol": "AAPL", "strategy": "Cash Secured Put", "rationale": "Support at 180"},
                    {"symbol": "MSFT", "strategy": "Iron Condor", "rationale": "Range bound"},
                    {"symbol": "GOOGL", "strategy": "Bull Put Spread", "rationale": "Cloud growth"}
                ]
            }
        }
        mock_response.raise_for_status = Mock()
        tool._client = Mock()
        tool._client.post.return_value = mock_response

        result = tool.execute("Find options")

        # Should only include top 3
        assert "RECOMMENDATION 1" in result
        assert "RECOMMENDATION 2" in result
        assert "RECOMMENDATION 3" in result
        assert "RECOMMENDATION 4" not in result
        assert "NVDA" in result
        assert "AAPL" in result
        assert "MSFT" in result

    @patch("tools.alpha_copilot.Config")
    def test_formats_all_metrics(self, mock_config):
        """Test formatting includes all available metrics."""
        mock_config.ALPHA_COPILOT_API_URL = "https://api.test.com"
        mock_config.ALPHA_COPILOT_API_KEY = "test_key"
        mock_config.validate_supabase.return_value = False

        from tools.alpha_copilot import QueryAlphaCopilotTool
        tool = QueryAlphaCopilotTool()

        mock_response = Mock()
        mock_response.json.return_value = {
            "status": "success",
            "analysis": {
                "market_overview": "Bullish",
                "recommendations": [{
                    "symbol": "NVDA",
                    "strategy": "Covered Call",
                    "strike": 950,
                    "premium": 12.50,
                    "probability_of_profit": 75,
                    "expiration": "Jan 17",
                    "delta": 0.30,
                    "rationale": "Strong technical setup"
                }]
            }
        }
        mock_response.raise_for_status = Mock()
        tool._client = Mock()
        tool._client.post.return_value = mock_response

        result = tool.execute("Find options")

        assert "Strike: $950" in result
        assert "Premium: $12.5" in result
        assert "POP: 75%" in result
        assert "Exp: Jan 17" in result
        assert "Delta: 0.3" in result
