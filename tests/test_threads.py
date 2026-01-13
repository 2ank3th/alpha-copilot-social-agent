"""Tests for Threads platform adapter."""

import pytest
from unittest.mock import Mock, patch, MagicMock
import httpx


class TestThreadsPlatformInit:
    """Tests for ThreadsPlatform initialization."""

    @patch("platforms.threads.Config")
    def test_init_with_credentials(self, mock_config):
        """Test initialization with valid Threads credentials."""
        mock_config.THREADS_ACCESS_TOKEN = "test_token"
        mock_config.THREADS_USER_ID = "user123"

        from platforms.threads import ThreadsPlatform
        platform = ThreadsPlatform()

        assert platform._access_token == "test_token"
        assert platform._user_id == "user123"
        assert platform._is_configured is True

    @patch("platforms.threads.Config")
    def test_init_without_credentials(self, mock_config):
        """Test initialization without credentials."""
        mock_config.THREADS_ACCESS_TOKEN = None
        mock_config.THREADS_USER_ID = None

        from platforms.threads import ThreadsPlatform
        platform = ThreadsPlatform()

        assert platform._is_configured is False


class TestThreadsPublish:
    """Tests for ThreadsPlatform.publish() method."""

    @patch("platforms.threads.Config")
    def test_publish_dry_run_mode(self, mock_config):
        """Test publish in dry run mode."""
        mock_config.DRY_RUN = True
        mock_config.THREADS_ACCESS_TOKEN = "token"
        mock_config.THREADS_USER_ID = "user123"

        from platforms.threads import ThreadsPlatform
        platform = ThreadsPlatform()
        result = platform.publish("Test Threads post")

        assert result["success"] is True
        assert result["dry_run"] is True
        assert "dry_run" in result["url"]

    @patch("platforms.threads.Config")
    def test_publish_without_credentials(self, mock_config):
        """Test publish when credentials not configured."""
        mock_config.DRY_RUN = False
        mock_config.THREADS_ACCESS_TOKEN = None
        mock_config.THREADS_USER_ID = None

        from platforms.threads import ThreadsPlatform
        platform = ThreadsPlatform()
        result = platform.publish("Test post")

        assert result["success"] is False
        assert "not configured" in result["error"]

    @patch("platforms.threads.time.sleep")
    @patch("platforms.threads.Config")
    def test_publish_success(self, mock_config, mock_sleep):
        """Test successful Threads publication."""
        mock_config.DRY_RUN = False
        mock_config.THREADS_ACCESS_TOKEN = "token"
        mock_config.THREADS_USER_ID = "user123"

        from platforms.threads import ThreadsPlatform
        platform = ThreadsPlatform()

        # Mock HTTP client
        mock_response_container = Mock()
        mock_response_container.json.return_value = {"id": "container123"}
        mock_response_container.raise_for_status = Mock()

        mock_response_publish = Mock()
        mock_response_publish.json.return_value = {"id": "post123"}
        mock_response_publish.raise_for_status = Mock()

        platform._client = Mock()
        platform._client.post.side_effect = [mock_response_container, mock_response_publish]

        result = platform.publish("Test post")

        assert result["success"] is True
        assert result["post_id"] == "post123"
        assert "post123" in result["url"]

    @patch("platforms.threads.time.sleep")
    @patch("platforms.threads.Config")
    def test_publish_with_reply_to(self, mock_config, mock_sleep):
        """Test publishing as a reply (thread)."""
        mock_config.DRY_RUN = False
        mock_config.THREADS_ACCESS_TOKEN = "token"
        mock_config.THREADS_USER_ID = "user123"

        from platforms.threads import ThreadsPlatform
        platform = ThreadsPlatform()

        mock_response_container = Mock()
        mock_response_container.json.return_value = {"id": "container123"}
        mock_response_container.raise_for_status = Mock()

        mock_response_publish = Mock()
        mock_response_publish.json.return_value = {"id": "reply123"}
        mock_response_publish.raise_for_status = Mock()

        platform._client = Mock()
        platform._client.post.side_effect = [mock_response_container, mock_response_publish]

        result = platform.publish("Reply post", reply_to_id="original123")

        # Verify reply_to_id was passed in params
        container_call = platform._client.post.call_args_list[0]
        params = container_call[1]["params"]
        assert params["reply_to_id"] == "original123"
        assert result["success"] is True

    @patch("platforms.threads.time.sleep")
    @patch("platforms.threads.Config")
    def test_publish_container_creation_fails(self, mock_config, mock_sleep):
        """Test publish when container creation fails."""
        mock_config.DRY_RUN = False
        mock_config.THREADS_ACCESS_TOKEN = "token"
        mock_config.THREADS_USER_ID = "user123"

        from platforms.threads import ThreadsPlatform
        platform = ThreadsPlatform()

        platform._client = Mock()
        platform._client.post.side_effect = Exception("Container creation failed")

        result = platform.publish("Test post")

        assert result["success"] is False
        assert "container" in result["error"].lower()

    @patch("platforms.threads.time.sleep")
    @patch("platforms.threads.Config")
    def test_publish_container_returns_none(self, mock_config, mock_sleep):
        """Test publish when container returns no ID."""
        mock_config.DRY_RUN = False
        mock_config.THREADS_ACCESS_TOKEN = "token"
        mock_config.THREADS_USER_ID = "user123"

        from platforms.threads import ThreadsPlatform
        platform = ThreadsPlatform()

        mock_response = Mock()
        mock_response.json.return_value = {}  # No ID
        mock_response.raise_for_status = Mock()

        platform._client = Mock()
        platform._client.post.return_value = mock_response

        result = platform.publish("Test post")

        assert result["success"] is False
        assert "container" in result["error"].lower()

    @patch("platforms.threads.time.sleep")
    @patch("platforms.threads.Config")
    def test_publish_publish_container_fails(self, mock_config, mock_sleep):
        """Test publish when publish_container step fails."""
        mock_config.DRY_RUN = False
        mock_config.THREADS_ACCESS_TOKEN = "token"
        mock_config.THREADS_USER_ID = "user123"

        from platforms.threads import ThreadsPlatform
        platform = ThreadsPlatform()

        # First call succeeds (container creation)
        mock_response_container = Mock()
        mock_response_container.json.return_value = {"id": "container123"}
        mock_response_container.raise_for_status = Mock()

        # Second call fails (publish)
        platform._client = Mock()
        platform._client.post.side_effect = [
            mock_response_container,
            Exception("Publish failed")
        ]

        result = platform.publish("Test post")

        assert result["success"] is False
        assert "error" in result

    @patch("platforms.threads.time.sleep")
    @patch("platforms.threads.Config")
    def test_publish_truncates_long_content(self, mock_config, mock_sleep):
        """Test that publish truncates content to max length (500)."""
        mock_config.DRY_RUN = False
        mock_config.THREADS_ACCESS_TOKEN = "token"
        mock_config.THREADS_USER_ID = "user123"

        from platforms.threads import ThreadsPlatform
        platform = ThreadsPlatform()

        mock_response_container = Mock()
        mock_response_container.json.return_value = {"id": "container123"}
        mock_response_container.raise_for_status = Mock()

        mock_response_publish = Mock()
        mock_response_publish.json.return_value = {"id": "post123"}
        mock_response_publish.raise_for_status = Mock()

        platform._client = Mock()
        platform._client.post.side_effect = [mock_response_container, mock_response_publish]

        # Create content longer than 500 chars
        long_content = "A" * 600
        result = platform.publish(long_content)

        # Verify content was truncated
        container_call = platform._client.post.call_args_list[0]
        params = container_call[1]["params"]
        assert len(params["text"]) <= 500
        assert result["success"] is True

    @patch("platforms.threads.Config")
    def test_publish_handles_general_exception(self, mock_config):
        """Test publish handles general exceptions."""
        mock_config.DRY_RUN = False
        mock_config.THREADS_ACCESS_TOKEN = "token"
        mock_config.THREADS_USER_ID = "user123"

        from platforms.threads import ThreadsPlatform
        platform = ThreadsPlatform()
        platform._client = Mock()
        platform._client.post.side_effect = Exception("Unexpected error")

        result = platform.publish("Test post")

        assert result["success"] is False
        # The error is wrapped in the container creation failure message
        assert "container" in result["error"].lower() or "Unexpected error" in result["error"]


class TestThreadsGetRecentPosts:
    """Tests for ThreadsPlatform.get_recent_posts() method."""

    @patch("platforms.threads.Config")
    def test_get_recent_posts_not_configured(self, mock_config):
        """Test get_recent_posts when not configured."""
        mock_config.THREADS_ACCESS_TOKEN = None
        mock_config.THREADS_USER_ID = None

        from platforms.threads import ThreadsPlatform
        platform = ThreadsPlatform()
        posts = platform.get_recent_posts()

        assert posts == []

    @patch("platforms.threads.Config")
    def test_get_recent_posts_success(self, mock_config):
        """Test successful retrieval of recent posts."""
        mock_config.THREADS_ACCESS_TOKEN = "token"
        mock_config.THREADS_USER_ID = "user123"

        from platforms.threads import ThreadsPlatform
        platform = ThreadsPlatform()

        mock_response = Mock()
        mock_response.json.return_value = {
            "data": [
                {"id": "post1", "text": "First post", "timestamp": "2024-01-15T10:00:00Z"},
                {"id": "post2", "text": "Second post", "timestamp": "2024-01-15T09:00:00Z"}
            ]
        }
        mock_response.raise_for_status = Mock()

        platform._client = Mock()
        platform._client.get.return_value = mock_response

        posts = platform.get_recent_posts()

        assert len(posts) == 2
        assert posts[0]["id"] == "post1"
        assert posts[0]["content"] == "First post"
        assert posts[1]["id"] == "post2"

    @patch("platforms.threads.Config")
    def test_get_recent_posts_empty_response(self, mock_config):
        """Test get_recent_posts with empty response."""
        mock_config.THREADS_ACCESS_TOKEN = "token"
        mock_config.THREADS_USER_ID = "user123"

        from platforms.threads import ThreadsPlatform
        platform = ThreadsPlatform()

        mock_response = Mock()
        mock_response.json.return_value = {"data": []}
        mock_response.raise_for_status = Mock()

        platform._client = Mock()
        platform._client.get.return_value = mock_response

        posts = platform.get_recent_posts()

        assert posts == []

    @patch("platforms.threads.Config")
    def test_get_recent_posts_handles_exception(self, mock_config):
        """Test get_recent_posts handles exceptions."""
        mock_config.THREADS_ACCESS_TOKEN = "token"
        mock_config.THREADS_USER_ID = "user123"

        from platforms.threads import ThreadsPlatform
        platform = ThreadsPlatform()
        platform._client = Mock()
        platform._client.get.side_effect = Exception("API Error")

        posts = platform.get_recent_posts()

        assert posts == []


class TestThreadsHealthCheck:
    """Tests for ThreadsPlatform.health_check() method."""

    @patch("platforms.threads.Config")
    def test_health_check_not_configured(self, mock_config):
        """Test health_check when not configured."""
        mock_config.THREADS_ACCESS_TOKEN = None
        mock_config.THREADS_USER_ID = None

        from platforms.threads import ThreadsPlatform
        platform = ThreadsPlatform()
        result = platform.health_check()

        assert result is False

    @patch("platforms.threads.Config")
    def test_health_check_success(self, mock_config):
        """Test health_check returns True with valid credentials."""
        mock_config.THREADS_ACCESS_TOKEN = "token"
        mock_config.THREADS_USER_ID = "user123"

        from platforms.threads import ThreadsPlatform
        platform = ThreadsPlatform()

        mock_response = Mock()
        mock_response.json.return_value = {"id": "user123", "username": "testuser"}
        mock_response.raise_for_status = Mock()

        platform._client = Mock()
        platform._client.get.return_value = mock_response

        result = platform.health_check()

        assert result is True

    @patch("platforms.threads.Config")
    def test_health_check_no_id_in_response(self, mock_config):
        """Test health_check returns False when no id in response."""
        mock_config.THREADS_ACCESS_TOKEN = "token"
        mock_config.THREADS_USER_ID = "user123"

        from platforms.threads import ThreadsPlatform
        platform = ThreadsPlatform()

        mock_response = Mock()
        mock_response.json.return_value = {"username": "testuser"}  # No id
        mock_response.raise_for_status = Mock()

        platform._client = Mock()
        platform._client.get.return_value = mock_response

        result = platform.health_check()

        assert result is False

    @patch("platforms.threads.Config")
    def test_health_check_handles_exception(self, mock_config):
        """Test health_check handles exceptions."""
        mock_config.THREADS_ACCESS_TOKEN = "token"
        mock_config.THREADS_USER_ID = "user123"

        from platforms.threads import ThreadsPlatform
        platform = ThreadsPlatform()
        platform._client = Mock()
        platform._client.get.side_effect = Exception("API Error")

        result = platform.health_check()

        assert result is False


class TestThreadsPlatformProperties:
    """Tests for ThreadsPlatform properties."""

    @patch("platforms.threads.Config")
    def test_platform_name(self, mock_config):
        """Test platform name is 'threads'."""
        mock_config.THREADS_ACCESS_TOKEN = None
        mock_config.THREADS_USER_ID = None

        from platforms.threads import ThreadsPlatform
        platform = ThreadsPlatform()
        assert platform.name == "threads"

    @patch("platforms.threads.Config")
    def test_max_length(self, mock_config):
        """Test max length is 500."""
        mock_config.THREADS_ACCESS_TOKEN = None
        mock_config.THREADS_USER_ID = None

        from platforms.threads import ThreadsPlatform
        platform = ThreadsPlatform()
        assert platform.max_length == 500

    @patch("platforms.threads.Config")
    def test_api_base_url(self, mock_config):
        """Test API base URL is correct."""
        mock_config.THREADS_ACCESS_TOKEN = None
        mock_config.THREADS_USER_ID = None

        from platforms.threads import ThreadsPlatform
        platform = ThreadsPlatform()
        assert platform.API_BASE == "https://graph.threads.net/v1.0"


class TestThreadsCreateContainer:
    """Tests for ThreadsPlatform._create_container() method."""

    @patch("platforms.threads.Config")
    def test_create_container_success(self, mock_config):
        """Test successful container creation."""
        mock_config.THREADS_ACCESS_TOKEN = "token"
        mock_config.THREADS_USER_ID = "user123"

        from platforms.threads import ThreadsPlatform
        platform = ThreadsPlatform()

        mock_response = Mock()
        mock_response.json.return_value = {"id": "container123"}
        mock_response.raise_for_status = Mock()

        platform._client = Mock()
        platform._client.post.return_value = mock_response

        container_id = platform._create_container("Test content")

        assert container_id == "container123"

    @patch("platforms.threads.Config")
    def test_create_container_with_reply(self, mock_config):
        """Test container creation with reply_to_id."""
        mock_config.THREADS_ACCESS_TOKEN = "token"
        mock_config.THREADS_USER_ID = "user123"

        from platforms.threads import ThreadsPlatform
        platform = ThreadsPlatform()

        mock_response = Mock()
        mock_response.json.return_value = {"id": "container123"}
        mock_response.raise_for_status = Mock()

        platform._client = Mock()
        platform._client.post.return_value = mock_response

        container_id = platform._create_container("Reply content", reply_to_id="original123")

        call_params = platform._client.post.call_args[1]["params"]
        assert call_params["reply_to_id"] == "original123"
        assert container_id == "container123"

    @patch("platforms.threads.Config")
    def test_create_container_failure(self, mock_config):
        """Test container creation failure."""
        mock_config.THREADS_ACCESS_TOKEN = "token"
        mock_config.THREADS_USER_ID = "user123"

        from platforms.threads import ThreadsPlatform
        platform = ThreadsPlatform()
        platform._client = Mock()
        platform._client.post.side_effect = Exception("API Error")

        container_id = platform._create_container("Test content")

        assert container_id is None


class TestThreadsPublishContainer:
    """Tests for ThreadsPlatform._publish_container() method."""

    @patch("platforms.threads.Config")
    def test_publish_container_success(self, mock_config):
        """Test successful container publish."""
        mock_config.THREADS_ACCESS_TOKEN = "token"
        mock_config.THREADS_USER_ID = "user123"

        from platforms.threads import ThreadsPlatform
        platform = ThreadsPlatform()

        mock_response = Mock()
        mock_response.json.return_value = {"id": "post123"}
        mock_response.raise_for_status = Mock()

        platform._client = Mock()
        platform._client.post.return_value = mock_response

        result = platform._publish_container("container123")

        assert result == {"id": "post123"}

    @patch("platforms.threads.Config")
    def test_publish_container_failure(self, mock_config):
        """Test container publish failure."""
        mock_config.THREADS_ACCESS_TOKEN = "token"
        mock_config.THREADS_USER_ID = "user123"

        from platforms.threads import ThreadsPlatform
        platform = ThreadsPlatform()
        platform._client = Mock()
        platform._client.post.side_effect = Exception("Publish failed")

        result = platform._publish_container("container123")

        assert "error" in result
        assert "Publish failed" in result["error"]


class TestThreadsCleanup:
    """Tests for ThreadsPlatform cleanup."""

    @patch("platforms.threads.Config")
    def test_del_closes_client(self, mock_config):
        """Test __del__ closes HTTP client."""
        mock_config.THREADS_ACCESS_TOKEN = "token"
        mock_config.THREADS_USER_ID = "user123"

        from platforms.threads import ThreadsPlatform
        platform = ThreadsPlatform()
        mock_client = Mock()
        platform._client = mock_client

        del platform

        mock_client.close.assert_called_once()
