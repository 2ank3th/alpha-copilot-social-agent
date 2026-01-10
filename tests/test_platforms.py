"""Tests for platform adapters."""

import pytest
from unittest.mock import patch, MagicMock
from platforms.base import BasePlatform
from platforms.twitter import TwitterPlatform
from platforms.threads import ThreadsPlatform


class TestBasePlatform:
    """Tests for BasePlatform class."""

    def test_truncate_content_short(self):
        """Test that short content is not truncated."""
        # Create a concrete implementation for testing
        class TestPlatform(BasePlatform):
            name = "test"
            max_length = 100

            def publish(self, content, reply_to_id=None):
                return {}

            def get_recent_posts(self, hours=24):
                return []

            def health_check(self):
                return True

        platform = TestPlatform()
        content = "Short content"
        result = platform.truncate_content(content)

        assert result == content

    def test_truncate_content_long(self):
        """Test that long content is truncated with ellipsis."""
        class TestPlatform(BasePlatform):
            name = "test"
            max_length = 20

            def publish(self, content, reply_to_id=None):
                return {}

            def get_recent_posts(self, hours=24):
                return []

            def health_check(self):
                return True

        platform = TestPlatform()
        content = "This is a very long content that exceeds the limit"
        result = platform.truncate_content(content)

        assert len(result) == 20
        assert result.endswith("...")


class TestTwitterPlatform:
    """Tests for TwitterPlatform class."""

    def test_max_length_is_280(self):
        """Test that Twitter max length is 280."""
        assert TwitterPlatform.max_length == 280

    def test_name_is_twitter(self):
        """Test that platform name is twitter."""
        assert TwitterPlatform.name == "twitter"

    @patch('platforms.twitter.Config')
    def test_dry_run_returns_success(self, mock_config):
        """Test that dry run mode returns success."""
        mock_config.DRY_RUN = True
        mock_config.validate_twitter.return_value = False
        mock_config.TWITTER_BEARER_TOKEN = None
        mock_config.TWITTER_API_KEY = None
        mock_config.TWITTER_API_SECRET = None
        mock_config.TWITTER_ACCESS_TOKEN = None
        mock_config.TWITTER_ACCESS_SECRET = None

        platform = TwitterPlatform()
        result = platform.publish("Test content")

        assert result["success"] is True
        assert result["dry_run"] is True

    @patch('platforms.twitter.Config')
    def test_publish_without_client_fails(self, mock_config):
        """Test that publish fails without client."""
        mock_config.DRY_RUN = False
        mock_config.validate_twitter.return_value = False
        mock_config.TWITTER_BEARER_TOKEN = None
        mock_config.TWITTER_API_KEY = None
        mock_config.TWITTER_API_SECRET = None
        mock_config.TWITTER_ACCESS_TOKEN = None
        mock_config.TWITTER_ACCESS_SECRET = None

        platform = TwitterPlatform()
        result = platform.publish("Test content")

        assert result["success"] is False
        assert "not initialized" in result["error"]


class TestThreadsPlatform:
    """Tests for ThreadsPlatform class."""

    def test_max_length_is_500(self):
        """Test that Threads max length is 500."""
        assert ThreadsPlatform.max_length == 500

    def test_name_is_threads(self):
        """Test that platform name is threads."""
        assert ThreadsPlatform.name == "threads"

    @patch('platforms.threads.Config')
    def test_dry_run_returns_success(self, mock_config):
        """Test that dry run mode returns success."""
        mock_config.DRY_RUN = True
        mock_config.THREADS_ACCESS_TOKEN = None
        mock_config.THREADS_USER_ID = None

        platform = ThreadsPlatform()
        result = platform.publish("Test content")

        assert result["success"] is True
        assert result["dry_run"] is True

    @patch('platforms.threads.Config')
    def test_publish_without_credentials_fails(self, mock_config):
        """Test that publish fails without credentials."""
        mock_config.DRY_RUN = False
        mock_config.THREADS_ACCESS_TOKEN = None
        mock_config.THREADS_USER_ID = None

        platform = ThreadsPlatform()
        result = platform.publish("Test content")

        assert result["success"] is False
        assert "not configured" in result["error"]
