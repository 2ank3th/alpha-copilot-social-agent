"""Tests for publish tools."""

import pytest
from unittest.mock import Mock, patch, MagicMock


class TestPublishTool:
    """Tests for PublishTool class."""

    def test_publish_tool_schema(self):
        """Test PublishTool schema definition."""
        from tools.publish import PublishTool

        tool = PublishTool()
        schema = tool.get_schema()

        assert schema["name"] == "publish"
        assert "content" in schema["parameters"]["properties"]
        assert "platform" in schema["parameters"]["properties"]
        assert "content" in schema["parameters"]["required"]
        assert "platform" in schema["parameters"]["required"]

    def test_publish_to_twitter_success(self):
        """Test successful publish to Twitter."""
        from tools.publish import PublishTool

        mock_platform = Mock()
        mock_platform.publish.return_value = {
            "success": True,
            "post_id": "123",
            "url": "https://twitter.com/123"
        }

        tool = PublishTool()
        # Inject mock platform directly
        tool._platform_instances["twitter"] = mock_platform
        result = tool.execute("Test content", "twitter")

        assert "SUCCESS" in result
        assert "123" in result

    def test_publish_dry_run(self):
        """Test publish in dry run mode."""
        from tools.publish import PublishTool

        mock_platform = Mock()
        mock_platform.publish.return_value = {
            "success": True,
            "post_id": "dry_run_id",
            "url": "https://twitter.com/dry_run",
            "dry_run": True
        }

        tool = PublishTool()
        tool._platform_instances["twitter"] = mock_platform
        result = tool.execute("Test content", "twitter")

        assert "DRY_RUN" in result

    def test_publish_unsupported_platform(self):
        """Test publish to unsupported platform returns error."""
        from tools.publish import PublishTool

        tool = PublishTool()
        result = tool.execute("Test content", "instagram")

        assert "ERROR" in result
        assert "not supported" in result

    def test_publish_failure(self):
        """Test publish failure returns error message."""
        from tools.publish import PublishTool

        mock_platform = Mock()
        mock_platform.publish.return_value = {
            "success": False,
            "error": "Rate limit exceeded"
        }

        tool = PublishTool()
        tool._platform_instances["twitter"] = mock_platform
        result = tool.execute("Test content", "twitter")

        assert "ERROR" in result
        assert "Rate limit" in result


class TestCheckRecentPostsTool:
    """Tests for CheckRecentPostsTool class."""

    def test_check_recent_posts_schema(self):
        """Test CheckRecentPostsTool schema definition."""
        from tools.publish import CheckRecentPostsTool

        tool = CheckRecentPostsTool()
        schema = tool.get_schema()

        assert schema["name"] == "check_recent_posts"
        assert "platform" in schema["parameters"]["properties"]
        assert "hours" in schema["parameters"]["properties"]

    def test_check_recent_posts_success(self):
        """Test successful retrieval of recent posts."""
        from tools.publish import CheckRecentPostsTool

        mock_platform = Mock()
        mock_platform.get_recent_posts.return_value = [
            {"content": "Post 1", "created_at": "2024-01-15T10:00:00Z"},
            {"content": "Post 2", "created_at": "2024-01-15T09:00:00Z"}
        ]

        tool = CheckRecentPostsTool()
        tool._platform_instances["twitter"] = mock_platform
        result = tool.execute("twitter")

        assert "RECENT_POSTS" in result
        assert "Post 1" in result

    def test_check_recent_posts_empty(self):
        """Test when no recent posts found."""
        from tools.publish import CheckRecentPostsTool

        mock_platform = Mock()
        mock_platform.get_recent_posts.return_value = []

        tool = CheckRecentPostsTool()
        tool._platform_instances["twitter"] = mock_platform
        result = tool.execute("twitter", hours=12)

        assert "NO_RECENT_POSTS" in result

    def test_check_recent_posts_unsupported_platform(self):
        """Test check_recent_posts with unsupported platform."""
        from tools.publish import CheckRecentPostsTool

        tool = CheckRecentPostsTool()
        result = tool.execute("instagram")

        assert "ERROR" in result
        assert "not supported" in result


class TestGetPlatformStatusTool:
    """Tests for GetPlatformStatusTool class."""

    def test_get_platform_status_schema(self):
        """Test GetPlatformStatusTool schema definition."""
        from tools.publish import GetPlatformStatusTool

        tool = GetPlatformStatusTool()
        schema = tool.get_schema()

        assert schema["name"] == "get_platform_status"
        assert "platform" in schema["parameters"]["properties"]

    def test_get_platform_status_available(self):
        """Test platform status when available."""
        from tools.publish import GetPlatformStatusTool

        mock_platform = Mock()
        mock_platform.health_check.return_value = True

        tool = GetPlatformStatusTool()
        tool._platform_instances["twitter"] = mock_platform
        result = tool.execute("twitter")

        assert "AVAILABLE" in result
        assert "ready to use" in result

    def test_get_platform_status_unavailable(self):
        """Test platform status when unavailable."""
        from tools.publish import GetPlatformStatusTool

        mock_platform = Mock()
        mock_platform.health_check.return_value = False

        tool = GetPlatformStatusTool()
        tool._platform_instances["twitter"] = mock_platform
        result = tool.execute("twitter")

        assert "UNAVAILABLE" in result
        assert "not configured" in result

    def test_get_platform_status_not_implemented(self):
        """Test platform status for non-existent platform."""
        from tools.publish import GetPlatformStatusTool

        tool = GetPlatformStatusTool()
        result = tool.execute("tiktok")

        assert "UNAVAILABLE" in result
        assert "not implemented" in result


class TestCrossPostTool:
    """Tests for CrossPostTool class."""

    def test_cross_post_schema(self):
        """Test CrossPostTool schema definition."""
        from tools.publish import CrossPostTool

        tool = CrossPostTool()
        schema = tool.get_schema()

        assert schema["name"] == "cross_post"
        assert "content" in schema["parameters"]["properties"]
        assert "include_promo" in schema["parameters"]["properties"]
        assert "content" in schema["parameters"]["required"]

    def test_cross_post_both_platforms(self):
        """Test cross-posting to both platforms."""
        from tools.publish import CrossPostTool

        mock_twitter_platform = Mock()
        mock_twitter_platform.publish.return_value = {"success": True, "post_id": "tw123", "url": "https://twitter.com/123"}
        mock_twitter_platform.truncate_content.return_value = "Test content"

        mock_threads_platform = Mock()
        mock_threads_platform.publish.return_value = {"success": True, "post_id": "th123", "url": "https://threads.net/123"}
        mock_threads_platform.truncate_content.return_value = "Test content"

        tool = CrossPostTool()
        tool._platform_instances["twitter"] = mock_twitter_platform
        tool._platform_instances["threads"] = mock_threads_platform
        result = tool.execute("Test content", include_promo=False)

        assert "CROSS_POST_RESULTS" in result
        assert "twitter" in result.lower()
        assert "threads" in result.lower()

    def test_cross_post_with_promo(self):
        """Test cross-posting with promotional follow-up."""
        from tools.publish import CrossPostTool

        mock_twitter_platform = Mock()
        mock_twitter_platform.publish.side_effect = [
            {"success": True, "post_id": "tw123", "url": "https://twitter.com/123"},
            {"success": True, "post_id": "tw_promo", "url": "https://twitter.com/promo"}
        ]
        mock_twitter_platform.truncate_content.return_value = "Test content"

        mock_threads_platform = Mock()
        mock_threads_platform.publish.side_effect = [
            {"success": True, "post_id": "th123", "url": "https://threads.net/123"},
            {"success": True, "post_id": "th_promo", "url": "https://threads.net/promo"}
        ]
        mock_threads_platform.truncate_content.return_value = "Test content"

        tool = CrossPostTool()
        tool._platform_instances["twitter"] = mock_twitter_platform
        tool._platform_instances["threads"] = mock_threads_platform
        result = tool.execute("Test content", include_promo=True)

        assert "PROMO" in result

    def test_cross_post_dry_run(self):
        """Test cross-posting in dry run mode."""
        from tools.publish import CrossPostTool

        mock_twitter_platform = Mock()
        mock_twitter_platform.publish.return_value = {"success": True, "dry_run": True}
        mock_twitter_platform.truncate_content.return_value = "Test content"

        mock_threads_platform = Mock()
        mock_threads_platform.publish.return_value = {"success": True, "dry_run": True}
        mock_threads_platform.truncate_content.return_value = "Test content"

        tool = CrossPostTool()
        tool._platform_instances["twitter"] = mock_twitter_platform
        tool._platform_instances["threads"] = mock_threads_platform
        result = tool.execute("Test content", include_promo=False)

        assert "DRY_RUN" in result

    def test_cross_post_partial_failure(self):
        """Test cross-posting when one platform fails."""
        from tools.publish import CrossPostTool

        mock_twitter_platform = Mock()
        mock_twitter_platform.publish.return_value = {"success": True, "post_id": "tw123", "url": "https://twitter.com/123"}
        mock_twitter_platform.truncate_content.return_value = "Test content"

        mock_threads_platform = Mock()
        mock_threads_platform.publish.return_value = {"success": False, "error": "API Error"}
        mock_threads_platform.truncate_content.return_value = "Test content"

        tool = CrossPostTool()
        tool._platform_instances["twitter"] = mock_twitter_platform
        tool._platform_instances["threads"] = mock_threads_platform
        result = tool.execute("Test content", include_promo=False)

        assert "SUCCESS" in result  # Twitter succeeded
        assert "FAILED" in result  # Threads failed

    def test_cross_post_promo_failure(self):
        """Test cross-posting when promo post fails."""
        from tools.publish import CrossPostTool

        mock_twitter_platform = Mock()
        mock_twitter_platform.publish.side_effect = [
            {"success": True, "post_id": "tw123", "url": "https://twitter.com/123"},
            {"success": False, "error": "Promo failed"}
        ]
        mock_twitter_platform.truncate_content.return_value = "Test content"

        mock_threads_platform = Mock()
        mock_threads_platform.publish.return_value = {"success": True, "post_id": "th123", "url": "https://threads.net/123"}
        mock_threads_platform.truncate_content.return_value = "Test content"

        tool = CrossPostTool()
        tool._platform_instances["twitter"] = mock_twitter_platform
        tool._platform_instances["threads"] = mock_threads_platform
        result = tool.execute("Test content", include_promo=True)

        assert "PROMO_FAILED" in result

    def test_cross_post_dry_run_with_promo(self):
        """Test cross-posting in dry run mode skips actual promo post."""
        from tools.publish import CrossPostTool

        mock_twitter_platform = Mock()
        mock_twitter_platform.publish.return_value = {"success": True, "dry_run": True}
        mock_twitter_platform.truncate_content.return_value = "Test content"

        mock_threads_platform = Mock()
        mock_threads_platform.publish.return_value = {"success": True, "dry_run": True}
        mock_threads_platform.truncate_content.return_value = "Test content"

        tool = CrossPostTool()
        tool._platform_instances["twitter"] = mock_twitter_platform
        tool._platform_instances["threads"] = mock_threads_platform
        result = tool.execute("Test content", include_promo=True)

        assert "promo thread" in result.lower()
        # Verify promo publish was not actually called (only main post)
        assert mock_twitter_platform.publish.call_count == 1


class TestDoneTool:
    """Tests for DoneTool class."""

    def test_done_tool_schema(self):
        """Test DoneTool schema definition."""
        from tools.publish import DoneTool

        tool = DoneTool()
        schema = tool.get_schema()

        assert schema["name"] == "done"
        assert "summary" in schema["parameters"]["properties"]
        assert "summary" in schema["parameters"]["required"]

    def test_done_tool_execute(self):
        """Test DoneTool returns completion message."""
        from tools.publish import DoneTool

        tool = DoneTool()
        result = tool.execute("Successfully posted to Twitter")

        assert "TASK_COMPLETE" in result
        assert "Successfully posted" in result


class TestPromoMessages:
    """Tests for promotional message templates."""

    def test_promo_messages_exist(self):
        """Test promo messages are defined for platforms."""
        from tools.publish import PROMO_MESSAGES

        assert "twitter" in PROMO_MESSAGES
        assert "threads" in PROMO_MESSAGES

    def test_promo_messages_have_url_placeholder(self):
        """Test promo messages contain url placeholder."""
        from tools.publish import PROMO_MESSAGES

        for platform, message in PROMO_MESSAGES.items():
            assert "{url}" in message


class TestPlatformRegistry:
    """Tests for platform registry."""

    def test_platforms_registered(self):
        """Test Twitter and Threads are registered."""
        from tools.publish import PLATFORMS

        assert "twitter" in PLATFORMS
        assert "threads" in PLATFORMS
