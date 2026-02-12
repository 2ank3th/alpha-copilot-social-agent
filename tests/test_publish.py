"""Tests for publish tools."""

import json
import os
import tempfile

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

    def test_check_recent_posts_uses_local_history_fallback(self):
        """Test local post history is used when API read access returns nothing."""
        from tools.publish import CheckRecentPostsTool, _record_post_history
        from agent.config import Config

        mock_platform = Mock()
        mock_platform.get_recent_posts.return_value = []

        tool = CheckRecentPostsTool()
        tool._platform_instances["twitter"] = mock_platform

        tmp = tempfile.NamedTemporaryFile(suffix=".json", delete=False)
        tmp.close()
        try:
            with patch.object(Config, "POST_HISTORY_PATH", tmp.name):
                _record_post_history(
                    platform="twitter",
                    content="$NVDA up 4% today",
                    post_id="123",
                    url="https://twitter.com/i/status/123",
                    is_promo=False,
                )
                result = tool.execute("twitter", hours=24)

            assert "RECENT_POSTS" in result
            assert "$NVDA" in result
        finally:
            if os.path.exists(tmp.name):
                os.remove(tmp.name)


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
        mock_twitter_platform.truncate_content.side_effect = lambda text: text

        mock_threads_platform = Mock()
        mock_threads_platform.publish.side_effect = [
            {"success": True, "post_id": "th123", "url": "https://threads.net/123"},
            {"success": True, "post_id": "th_promo", "url": "https://threads.net/promo"}
        ]
        mock_threads_platform.truncate_content.side_effect = lambda text: text

        tool = CrossPostTool()
        tool._platform_instances["twitter"] = mock_twitter_platform
        tool._platform_instances["threads"] = mock_threads_platform
        result = tool.execute("Test content", include_promo=True)

        assert "PROMO" in result
        assert "Variant v" in result

        # Promo follow-up should include platform-specific UTM tags
        twitter_promo_text = mock_twitter_platform.publish.call_args_list[1].args[0]
        threads_promo_text = mock_threads_platform.publish.call_args_list[1].args[0]
        assert "utm_source=twitter" in twitter_promo_text
        assert "utm_source=threads" in threads_promo_text

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

    def test_cross_post_records_history_when_live_mode(self):
        """Test successful live cross-post records entries in local history."""
        from tools.publish import CrossPostTool
        from agent.config import Config

        mock_twitter_platform = Mock()
        mock_twitter_platform.publish.return_value = {
            "success": True,
            "post_id": "tw123",
            "url": "https://twitter.com/123",
        }
        mock_twitter_platform.truncate_content.side_effect = lambda text: text

        mock_threads_platform = Mock()
        mock_threads_platform.publish.return_value = {
            "success": True,
            "post_id": "th123",
            "url": "https://threads.net/123",
        }
        mock_threads_platform.truncate_content.side_effect = lambda text: text

        tool = CrossPostTool()
        tool._platform_instances["twitter"] = mock_twitter_platform
        tool._platform_instances["threads"] = mock_threads_platform

        tmp = tempfile.NamedTemporaryFile(suffix=".json", delete=False)
        tmp.close()

        try:
            with patch.object(Config, "DRY_RUN", False):
                with patch.object(Config, "POST_HISTORY_PATH", tmp.name):
                    tool.execute("Test content", include_promo=False)

            with open(tmp.name, "r", encoding="utf-8") as f:
                history = json.load(f)

            # One main post entry per platform
            non_promo_entries = [entry for entry in history if not entry.get("is_promo")]
            assert len(non_promo_entries) == 2
            platforms = {entry["platform"] for entry in non_promo_entries}
            assert platforms == {"twitter", "threads"}
        finally:
            if os.path.exists(tmp.name):
                os.remove(tmp.name)


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

    def test_extract_primary_ticker(self):
        """Test ticker extraction from post content."""
        from tools.publish import CrossPostTool

        tool = CrossPostTool()
        assert tool._extract_primary_ticker("$NVDA up 5% today") == "$NVDA"
        assert tool._extract_primary_ticker("No ticker in this post") == "this setup"

    def test_get_promo_message_includes_ticker_and_utm(self):
        """Test promo messages are personalized and trackable."""
        from tools.publish import CrossPostTool
        from agent.config import Config

        tool = CrossPostTool()
        with patch.object(Config, "ALPHA_COPILOT_URL", "https://alphacopilot.app"):
            with patch.object(Config, "ALPHA_COPILOT_UTM_MEDIUM", "social"):
                with patch.object(Config, "ALPHA_COPILOT_UTM_CAMPAIGN", "qa-campaign"):
                    with patch.object(Config, "ALPHA_COPILOT_UTM_CONTENT_PREFIX", "promo-thread"):
                        message, variant = tool._get_promo_message(
                            "twitter",
                            "$TSLA down 6% today",
                        )

        assert "$TSLA" in message
        assert "utm_source=twitter" in message
        assert "utm_medium=social" in message
        assert "utm_campaign=qa-campaign" in message
        assert "utm_content=promo-thread-v" in message
        assert variant >= 1

    def test_build_tracking_url_preserves_existing_query(self):
        """Test UTM builder keeps existing query params."""
        from tools.publish import CrossPostTool
        from agent.config import Config

        tool = CrossPostTool()
        with patch.object(Config, "ALPHA_COPILOT_URL", "https://alphacopilot.app/?ref=profile"):
            with patch.object(Config, "ALPHA_COPILOT_UTM_MEDIUM", "social"):
                with patch.object(Config, "ALPHA_COPILOT_UTM_CAMPAIGN", "campaign"):
                    with patch.object(Config, "ALPHA_COPILOT_UTM_CONTENT_PREFIX", "promo"):
                        url = tool._build_tracking_url("twitter", 1)

        assert "ref=profile" in url
        assert "utm_source=twitter" in url
        assert "utm_content=promo-v2" in url


class TestCrossPostWithImage:
    """Tests for CrossPostTool with image attachment."""

    def test_cross_post_schema_has_image_path(self):
        """Test CrossPostTool schema includes image_path parameter."""
        from tools.publish import CrossPostTool

        tool = CrossPostTool()
        schema = tool.get_schema()

        assert "image_path" in schema["parameters"]["properties"]

    def test_cross_post_with_image_uploads_to_twitter(self):
        """Test cross-posting with image uploads media to Twitter."""
        from tools.publish import CrossPostTool
        import tempfile
        import os

        # Create a temp file to simulate an image
        tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
        tmp.write(b"fake png data")
        tmp.close()

        mock_twitter = Mock()
        mock_twitter.upload_media.return_value = "media_123"
        mock_twitter.publish.return_value = {"success": True, "post_id": "tw123", "url": "https://twitter.com/123"}
        mock_twitter.truncate_content.return_value = "Test content"

        mock_threads = Mock()
        mock_threads.publish.return_value = {"success": True, "post_id": "th123", "url": "https://threads.net/123"}
        mock_threads.truncate_content.return_value = "Test content"

        tool = CrossPostTool()
        tool._platform_instances["twitter"] = mock_twitter
        tool._platform_instances["threads"] = mock_threads
        result = tool.execute("Test content", include_promo=False, image_path=tmp.name)

        # Twitter should have upload_media called
        mock_twitter.upload_media.assert_called_once_with(tmp.name)
        # Twitter publish should have media_ids
        mock_twitter.publish.assert_called_once_with("Test content", media_ids=["media_123"])
        # Threads should not have media_ids
        mock_threads.publish.assert_called_once_with("Test content", media_ids=None)

        assert "CROSS_POST_RESULTS" in result

    def test_cross_post_image_upload_failure_falls_back_to_text(self):
        """Test that image upload failure gracefully falls back to text-only."""
        from tools.publish import CrossPostTool
        import tempfile

        tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
        tmp.write(b"fake png data")
        tmp.close()

        mock_twitter = Mock()
        mock_twitter.upload_media.side_effect = Exception("Upload failed")
        mock_twitter.publish.return_value = {"success": True, "post_id": "tw123", "url": "https://twitter.com/123"}
        mock_twitter.truncate_content.return_value = "Test content"

        mock_threads = Mock()
        mock_threads.publish.return_value = {"success": True, "post_id": "th123", "url": "https://threads.net/123"}
        mock_threads.truncate_content.return_value = "Test content"

        tool = CrossPostTool()
        tool._platform_instances["twitter"] = mock_twitter
        tool._platform_instances["threads"] = mock_threads
        result = tool.execute("Test content", include_promo=False, image_path=tmp.name)

        # Should still succeed (text-only fallback)
        assert "SUCCESS" in result
        # Twitter should have been called without media_ids
        mock_twitter.publish.assert_called_once_with("Test content", media_ids=None)

    def test_cross_post_cleans_up_temp_image(self):
        """Test that temp image file is cleaned up after posting."""
        from tools.publish import CrossPostTool
        import tempfile
        import os

        tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
        tmp.write(b"fake png data")
        tmp.close()
        assert os.path.exists(tmp.name)

        mock_twitter = Mock()
        mock_twitter.publish.return_value = {"success": True, "dry_run": True}
        mock_twitter.truncate_content.return_value = "Test"

        mock_threads = Mock()
        mock_threads.publish.return_value = {"success": True, "dry_run": True}
        mock_threads.truncate_content.return_value = "Test"

        tool = CrossPostTool()
        tool._platform_instances["twitter"] = mock_twitter
        tool._platform_instances["threads"] = mock_threads
        tool.execute("Test", include_promo=False, image_path=tmp.name)

        # File should have been cleaned up
        assert not os.path.exists(tmp.name)


class TestPlatformRegistry:
    """Tests for platform registry."""

    def test_platforms_registered(self):
        """Test Twitter and Threads are registered."""
        from tools.publish import PLATFORMS

        assert "twitter" in PLATFORMS
        assert "threads" in PLATFORMS
