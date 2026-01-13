"""Tests for Supabase authentication."""

import pytest
from unittest.mock import Mock, patch, MagicMock
import httpx

from agent.supabase_auth import SupabaseAuth


class TestSupabaseAuthLogin:
    """Tests for SupabaseAuth.login() method."""

    @patch("agent.supabase_auth.Config")
    @patch("agent.supabase_auth.httpx.post")
    def test_login_success(self, mock_post, mock_config):
        """Successful login returns tokens."""
        mock_config.SUPABASE_URL = "https://test.supabase.co"
        mock_config.SUPABASE_ANON_KEY = "test_anon_key"
        mock_config.SUPABASE_EMAIL = "test@example.com"
        mock_config.SUPABASE_PASSWORD = "test_password"

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "test_access_token",
            "refresh_token": "test_refresh_token"
        }
        mock_post.return_value = mock_response

        auth = SupabaseAuth()
        success, msg = auth.login()

        assert success is True
        assert msg == "Login successful"
        assert auth._access_token == "test_access_token"
        assert auth._refresh_token == "test_refresh_token"

    @patch("agent.supabase_auth.Config")
    @patch("agent.supabase_auth.httpx.post")
    def test_login_invalid_credentials_400(self, mock_post, mock_config):
        """Login with invalid credentials returns 400 error."""
        mock_config.SUPABASE_URL = "https://test.supabase.co"
        mock_config.SUPABASE_ANON_KEY = "test_anon_key"
        mock_config.SUPABASE_EMAIL = "test@example.com"
        mock_config.SUPABASE_PASSWORD = "wrong_password"

        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.json.return_value = {"error_description": "Invalid login credentials"}
        mock_post.return_value = mock_response

        auth = SupabaseAuth()
        success, msg = auth.login()

        assert success is False
        assert "Invalid credentials" in msg
        assert auth._access_token is None

    @patch("agent.supabase_auth.Config")
    @patch("agent.supabase_auth.httpx.post")
    def test_login_invalid_email_422(self, mock_post, mock_config):
        """Login with invalid email format returns 422 error."""
        mock_config.SUPABASE_URL = "https://test.supabase.co"
        mock_config.SUPABASE_ANON_KEY = "test_anon_key"
        mock_config.SUPABASE_EMAIL = "invalid_email"
        mock_config.SUPABASE_PASSWORD = "password"

        mock_response = Mock()
        mock_response.status_code = 422
        mock_post.return_value = mock_response

        auth = SupabaseAuth()
        success, msg = auth.login()

        assert success is False
        assert "Invalid email format" in msg

    @patch("agent.supabase_auth.Config")
    def test_login_missing_credentials(self, mock_config):
        """Login with missing credentials reports missing fields."""
        mock_config.SUPABASE_URL = "https://test.supabase.co"
        mock_config.SUPABASE_ANON_KEY = None
        mock_config.SUPABASE_EMAIL = None
        mock_config.SUPABASE_PASSWORD = "password"

        auth = SupabaseAuth()
        success, msg = auth.login()

        assert success is False
        assert "Missing credentials" in msg
        assert "SUPABASE_ANON_KEY" in msg
        assert "SUPABASE_EMAIL" in msg

    @patch("agent.supabase_auth.Config")
    @patch("agent.supabase_auth.httpx.post")
    def test_login_connection_error(self, mock_post, mock_config):
        """Login handles connection error gracefully."""
        mock_config.SUPABASE_URL = "https://test.supabase.co"
        mock_config.SUPABASE_ANON_KEY = "test_anon_key"
        mock_config.SUPABASE_EMAIL = "test@example.com"
        mock_config.SUPABASE_PASSWORD = "password"

        mock_post.side_effect = httpx.ConnectError("Connection refused")

        auth = SupabaseAuth()
        success, msg = auth.login()

        assert success is False
        assert "Cannot connect to Supabase" in msg

    @patch("agent.supabase_auth.Config")
    @patch("agent.supabase_auth.httpx.post")
    def test_login_timeout(self, mock_post, mock_config):
        """Login handles timeout gracefully."""
        mock_config.SUPABASE_URL = "https://test.supabase.co"
        mock_config.SUPABASE_ANON_KEY = "test_anon_key"
        mock_config.SUPABASE_EMAIL = "test@example.com"
        mock_config.SUPABASE_PASSWORD = "password"

        mock_post.side_effect = httpx.TimeoutException("Request timeout")

        auth = SupabaseAuth()
        success, msg = auth.login()

        assert success is False
        assert "Login timeout" in msg

    @patch("agent.supabase_auth.Config")
    @patch("agent.supabase_auth.httpx.post")
    def test_login_server_error_500(self, mock_post, mock_config):
        """Login handles 500 server error."""
        mock_config.SUPABASE_URL = "https://test.supabase.co"
        mock_config.SUPABASE_ANON_KEY = "test_anon_key"
        mock_config.SUPABASE_EMAIL = "test@example.com"
        mock_config.SUPABASE_PASSWORD = "password"

        mock_response = Mock()
        mock_response.status_code = 500
        mock_post.return_value = mock_response

        auth = SupabaseAuth()
        success, msg = auth.login()

        assert success is False
        assert "HTTP 500" in msg


class TestSupabaseAuthGetToken:
    """Tests for SupabaseAuth.get_access_token() method."""

    @patch("agent.supabase_auth.Config")
    def test_get_token_returns_cached(self, mock_config):
        """Returns cached token if available."""
        mock_config.SUPABASE_URL = "https://test.supabase.co"
        mock_config.SUPABASE_ANON_KEY = "test_anon_key"
        mock_config.SUPABASE_EMAIL = "test@example.com"
        mock_config.SUPABASE_PASSWORD = "password"

        auth = SupabaseAuth()
        auth._access_token = "cached_token"

        token = auth.get_access_token()

        assert token == "cached_token"

    @patch("agent.supabase_auth.Config")
    @patch("agent.supabase_auth.httpx.post")
    def test_get_token_auto_login(self, mock_post, mock_config):
        """Auto-login when no cached token."""
        mock_config.SUPABASE_URL = "https://test.supabase.co"
        mock_config.SUPABASE_ANON_KEY = "test_anon_key"
        mock_config.SUPABASE_EMAIL = "test@example.com"
        mock_config.SUPABASE_PASSWORD = "password"

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "new_token",
            "refresh_token": "refresh_token"
        }
        mock_post.return_value = mock_response

        auth = SupabaseAuth()
        token = auth.get_access_token()

        assert token == "new_token"
        mock_post.assert_called_once()

    @patch("agent.supabase_auth.Config")
    @patch("agent.supabase_auth.httpx.post")
    def test_get_token_returns_none_on_failure(self, mock_post, mock_config):
        """Returns None when login fails."""
        mock_config.SUPABASE_URL = "https://test.supabase.co"
        mock_config.SUPABASE_ANON_KEY = "test_anon_key"
        mock_config.SUPABASE_EMAIL = "test@example.com"
        mock_config.SUPABASE_PASSWORD = "wrong"

        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.json.return_value = {"error_description": "Invalid credentials"}
        mock_post.return_value = mock_response

        auth = SupabaseAuth()
        token = auth.get_access_token()

        assert token is None


class TestSupabaseAuthRefresh:
    """Tests for SupabaseAuth.refresh() method."""

    @patch("agent.supabase_auth.Config")
    @patch("agent.supabase_auth.httpx.post")
    def test_refresh_success(self, mock_post, mock_config):
        """Successful token refresh updates tokens."""
        mock_config.SUPABASE_URL = "https://test.supabase.co"
        mock_config.SUPABASE_ANON_KEY = "test_anon_key"
        mock_config.SUPABASE_EMAIL = "test@example.com"
        mock_config.SUPABASE_PASSWORD = "password"

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "new_access_token",
            "refresh_token": "new_refresh_token"
        }
        mock_post.return_value = mock_response

        auth = SupabaseAuth()
        auth._refresh_token = "old_refresh_token"
        success, msg = auth.refresh()

        assert success is True
        assert msg == "Token refreshed"
        assert auth._access_token == "new_access_token"
        assert auth._refresh_token == "new_refresh_token"

    @patch("agent.supabase_auth.Config")
    @patch("agent.supabase_auth.httpx.post")
    def test_refresh_fallback_to_login_on_failure(self, mock_post, mock_config):
        """Falls back to login when refresh fails."""
        mock_config.SUPABASE_URL = "https://test.supabase.co"
        mock_config.SUPABASE_ANON_KEY = "test_anon_key"
        mock_config.SUPABASE_EMAIL = "test@example.com"
        mock_config.SUPABASE_PASSWORD = "password"

        # First call: refresh fails with 401
        # Second call: login succeeds
        refresh_response = Mock()
        refresh_response.status_code = 401

        login_response = Mock()
        login_response.status_code = 200
        login_response.json.return_value = {
            "access_token": "fresh_token",
            "refresh_token": "fresh_refresh"
        }

        mock_post.side_effect = [refresh_response, login_response]

        auth = SupabaseAuth()
        auth._refresh_token = "expired_refresh_token"
        success, msg = auth.refresh()

        assert success is True
        assert auth._access_token == "fresh_token"

    @patch("agent.supabase_auth.Config")
    @patch("agent.supabase_auth.httpx.post")
    def test_refresh_calls_login_when_no_refresh_token(self, mock_post, mock_config):
        """Calls login when no refresh token available."""
        mock_config.SUPABASE_URL = "https://test.supabase.co"
        mock_config.SUPABASE_ANON_KEY = "test_anon_key"
        mock_config.SUPABASE_EMAIL = "test@example.com"
        mock_config.SUPABASE_PASSWORD = "password"

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "new_token",
            "refresh_token": "new_refresh"
        }
        mock_post.return_value = mock_response

        auth = SupabaseAuth()
        auth._refresh_token = None  # No refresh token
        success, msg = auth.refresh()

        assert success is True
        assert msg == "Login successful"

    @patch("agent.supabase_auth.Config")
    @patch("agent.supabase_auth.httpx.post")
    def test_refresh_handles_exception(self, mock_post, mock_config):
        """Handles exception during refresh gracefully."""
        mock_config.SUPABASE_URL = "https://test.supabase.co"
        mock_config.SUPABASE_ANON_KEY = "test_anon_key"
        mock_config.SUPABASE_EMAIL = "test@example.com"
        mock_config.SUPABASE_PASSWORD = "password"

        mock_post.side_effect = Exception("Network error")

        auth = SupabaseAuth()
        auth._refresh_token = "some_token"
        success, msg = auth.refresh()

        assert success is False
        assert "Refresh error" in msg


class TestSupabaseAuthClearTokens:
    """Tests for SupabaseAuth.clear_tokens() method."""

    @patch("agent.supabase_auth.Config")
    def test_clear_tokens(self, mock_config):
        """Clear tokens removes cached tokens."""
        mock_config.SUPABASE_URL = "https://test.supabase.co"
        mock_config.SUPABASE_ANON_KEY = "test_anon_key"
        mock_config.SUPABASE_EMAIL = "test@example.com"
        mock_config.SUPABASE_PASSWORD = "password"

        auth = SupabaseAuth()
        auth._access_token = "some_token"
        auth._refresh_token = "some_refresh"

        auth.clear_tokens()

        assert auth._access_token is None
        assert auth._refresh_token is None
