"""Tests for Twitter platform adapter."""

import pytest
from unittest.mock import Mock, patch, MagicMock


class TestTwitterPlatformInit:
    """Tests for TwitterPlatform initialization."""

    @patch("platforms.twitter.Config")
    @patch("platforms.twitter.TWEEPY_AVAILABLE", True)
    def test_init_with_valid_credentials(self, mock_config):
        """Test initialization with valid Twitter credentials."""
        mock_config.validate_twitter.return_value = True
        mock_config.TWITTER_BEARER_TOKEN = "bearer_token"
        mock_config.TWITTER_API_KEY = "api_key"
        mock_config.TWITTER_API_SECRET = "api_secret"
        mock_config.TWITTER_ACCESS_TOKEN = "access_token"
        mock_config.TWITTER_ACCESS_SECRET = "access_secret"

        with patch("platforms.twitter.tweepy") as mock_tweepy:
            from platforms.twitter import TwitterPlatform
            platform = TwitterPlatform()
            assert platform._client is not None

    @patch("platforms.twitter.Config")
    @patch("platforms.twitter.TWEEPY_AVAILABLE", True)
    def test_init_without_credentials(self, mock_config):
        """Test initialization without Twitter credentials."""
        mock_config.validate_twitter.return_value = False

        from platforms.twitter import TwitterPlatform
        platform = TwitterPlatform()
        assert platform._client is None

    @patch("platforms.twitter.TWEEPY_AVAILABLE", False)
    @patch("platforms.twitter.Config")
    def test_init_without_tweepy(self, mock_config):
        """Test initialization when tweepy is not installed."""
        mock_config.validate_twitter.return_value = True

        from platforms.twitter import TwitterPlatform
        platform = TwitterPlatform()
        assert platform._client is None


class TestTwitterPublish:
    """Tests for TwitterPlatform.publish() method."""

    @patch("platforms.twitter.Config")
    def test_publish_dry_run_mode(self, mock_config):
        """Test publish in dry run mode."""
        mock_config.DRY_RUN = True
        mock_config.validate_twitter.return_value = False

        from platforms.twitter import TwitterPlatform
        platform = TwitterPlatform()
        result = platform.publish("Test tweet content")

        assert result["success"] is True
        assert result["dry_run"] is True
        assert "dry_run" in result["url"]

    @patch("platforms.twitter.Config")
    def test_publish_without_client(self, mock_config):
        """Test publish when client is not initialized."""
        mock_config.DRY_RUN = False
        mock_config.validate_twitter.return_value = False

        from platforms.twitter import TwitterPlatform
        platform = TwitterPlatform()
        result = platform.publish("Test tweet")

        assert result["success"] is False
        assert "not initialized" in result["error"]

    @patch("platforms.twitter.Config")
    @patch("platforms.twitter.TWEEPY_AVAILABLE", True)
    def test_publish_success(self, mock_config):
        """Test successful tweet publication."""
        mock_config.DRY_RUN = False
        mock_config.validate_twitter.return_value = True
        mock_config.TWITTER_BEARER_TOKEN = "bearer"
        mock_config.TWITTER_API_KEY = "key"
        mock_config.TWITTER_API_SECRET = "secret"
        mock_config.TWITTER_ACCESS_TOKEN = "token"
        mock_config.TWITTER_ACCESS_SECRET = "secret"

        with patch("platforms.twitter.tweepy") as mock_tweepy:
            mock_client = Mock()
            mock_response = Mock()
            mock_response.data = {"id": "12345"}
            mock_client.create_tweet.return_value = mock_response
            mock_tweepy.Client.return_value = mock_client

            from platforms.twitter import TwitterPlatform
            platform = TwitterPlatform()
            result = platform.publish("Test tweet")

            assert result["success"] is True
            assert result["post_id"] == "12345"
            assert "12345" in result["url"]

    @patch("platforms.twitter.Config")
    @patch("platforms.twitter.TWEEPY_AVAILABLE", True)
    def test_publish_with_reply_to(self, mock_config):
        """Test publishing as a reply (thread)."""
        mock_config.DRY_RUN = False
        mock_config.validate_twitter.return_value = True
        mock_config.TWITTER_BEARER_TOKEN = "bearer"
        mock_config.TWITTER_API_KEY = "key"
        mock_config.TWITTER_API_SECRET = "secret"
        mock_config.TWITTER_ACCESS_TOKEN = "token"
        mock_config.TWITTER_ACCESS_SECRET = "secret"

        with patch("platforms.twitter.tweepy") as mock_tweepy:
            mock_client = Mock()
            mock_response = Mock()
            mock_response.data = {"id": "67890"}
            mock_client.create_tweet.return_value = mock_response
            mock_tweepy.Client.return_value = mock_client

            from platforms.twitter import TwitterPlatform
            platform = TwitterPlatform()
            result = platform.publish("Reply tweet", reply_to_id="12345")

            mock_client.create_tweet.assert_called_with(
                text="Reply tweet",
                in_reply_to_tweet_id="12345"
            )
            assert result["success"] is True

    @patch("platforms.twitter.Config")
    @patch("platforms.twitter.TWEEPY_AVAILABLE", True)
    def test_publish_truncates_long_content(self, mock_config):
        """Test that publish truncates content to max length."""
        mock_config.DRY_RUN = False
        mock_config.validate_twitter.return_value = True
        mock_config.TWITTER_BEARER_TOKEN = "bearer"
        mock_config.TWITTER_API_KEY = "key"
        mock_config.TWITTER_API_SECRET = "secret"
        mock_config.TWITTER_ACCESS_TOKEN = "token"
        mock_config.TWITTER_ACCESS_SECRET = "secret"

        with patch("platforms.twitter.tweepy") as mock_tweepy:
            mock_client = Mock()
            mock_response = Mock()
            mock_response.data = {"id": "12345"}
            mock_client.create_tweet.return_value = mock_response
            mock_tweepy.Client.return_value = mock_client

            from platforms.twitter import TwitterPlatform
            platform = TwitterPlatform()

            # Create content longer than 280 chars
            long_content = "A" * 300
            result = platform.publish(long_content)

            # Verify content was truncated
            call_args = mock_client.create_tweet.call_args
            assert len(call_args[1]["text"]) <= 280
            assert result["success"] is True

    @patch("platforms.twitter.Config")
    @patch("platforms.twitter.TWEEPY_AVAILABLE", True)
    def test_publish_handles_exception(self, mock_config):
        """Test publish handles API exceptions."""
        mock_config.DRY_RUN = False
        mock_config.validate_twitter.return_value = True
        mock_config.TWITTER_BEARER_TOKEN = "bearer"
        mock_config.TWITTER_API_KEY = "key"
        mock_config.TWITTER_API_SECRET = "secret"
        mock_config.TWITTER_ACCESS_TOKEN = "token"
        mock_config.TWITTER_ACCESS_SECRET = "secret"

        with patch("platforms.twitter.tweepy") as mock_tweepy:
            mock_client = Mock()
            mock_client.create_tweet.side_effect = Exception("API Error")
            mock_tweepy.Client.return_value = mock_client

            from platforms.twitter import TwitterPlatform
            platform = TwitterPlatform()
            result = platform.publish("Test tweet")

            assert result["success"] is False
            assert "API Error" in result["error"]


class TestTwitterGetRecentPosts:
    """Tests for TwitterPlatform.get_recent_posts() method."""

    @patch("platforms.twitter.Config")
    def test_get_recent_posts_without_client(self, mock_config):
        """Test get_recent_posts returns empty when no client."""
        mock_config.validate_twitter.return_value = False

        from platforms.twitter import TwitterPlatform
        platform = TwitterPlatform()
        posts = platform.get_recent_posts()

        assert posts == []

    @patch("platforms.twitter.Config")
    @patch("platforms.twitter.TWEEPY_AVAILABLE", True)
    def test_get_recent_posts_success(self, mock_config):
        """Test successful retrieval of recent posts."""
        mock_config.validate_twitter.return_value = True
        mock_config.TWITTER_BEARER_TOKEN = "bearer"
        mock_config.TWITTER_API_KEY = "key"
        mock_config.TWITTER_API_SECRET = "secret"
        mock_config.TWITTER_ACCESS_TOKEN = "token"
        mock_config.TWITTER_ACCESS_SECRET = "secret"

        with patch("platforms.twitter.tweepy") as mock_tweepy:
            mock_client = Mock()

            # Mock get_me
            mock_me = Mock()
            mock_me.data = Mock(id="user123")
            mock_client.get_me.return_value = mock_me

            # Mock get_users_tweets
            from datetime import datetime
            mock_tweet = Mock()
            mock_tweet.id = 123
            mock_tweet.text = "Test tweet"
            mock_tweet.created_at = datetime.now()

            mock_tweets = Mock()
            mock_tweets.data = [mock_tweet]
            mock_client.get_users_tweets.return_value = mock_tweets

            mock_tweepy.Client.return_value = mock_client

            from platforms.twitter import TwitterPlatform
            platform = TwitterPlatform()
            posts = platform.get_recent_posts()

            assert len(posts) == 1
            assert posts[0]["id"] == "123"
            assert posts[0]["content"] == "Test tweet"

    @patch("platforms.twitter.Config")
    @patch("platforms.twitter.TWEEPY_AVAILABLE", True)
    def test_get_recent_posts_no_user(self, mock_config):
        """Test get_recent_posts when get_me returns no data."""
        mock_config.validate_twitter.return_value = True
        mock_config.TWITTER_BEARER_TOKEN = "bearer"
        mock_config.TWITTER_API_KEY = "key"
        mock_config.TWITTER_API_SECRET = "secret"
        mock_config.TWITTER_ACCESS_TOKEN = "token"
        mock_config.TWITTER_ACCESS_SECRET = "secret"

        with patch("platforms.twitter.tweepy") as mock_tweepy:
            mock_client = Mock()
            mock_me = Mock()
            mock_me.data = None
            mock_client.get_me.return_value = mock_me
            mock_tweepy.Client.return_value = mock_client

            from platforms.twitter import TwitterPlatform
            platform = TwitterPlatform()
            posts = platform.get_recent_posts()

            assert posts == []

    @patch("platforms.twitter.Config")
    @patch("platforms.twitter.TWEEPY_AVAILABLE", True)
    def test_get_recent_posts_no_tweets(self, mock_config):
        """Test get_recent_posts when no tweets exist."""
        mock_config.validate_twitter.return_value = True
        mock_config.TWITTER_BEARER_TOKEN = "bearer"
        mock_config.TWITTER_API_KEY = "key"
        mock_config.TWITTER_API_SECRET = "secret"
        mock_config.TWITTER_ACCESS_TOKEN = "token"
        mock_config.TWITTER_ACCESS_SECRET = "secret"

        with patch("platforms.twitter.tweepy") as mock_tweepy:
            mock_client = Mock()
            mock_me = Mock()
            mock_me.data = Mock(id="user123")
            mock_client.get_me.return_value = mock_me

            mock_tweets = Mock()
            mock_tweets.data = None
            mock_client.get_users_tweets.return_value = mock_tweets

            mock_tweepy.Client.return_value = mock_client

            from platforms.twitter import TwitterPlatform
            platform = TwitterPlatform()
            posts = platform.get_recent_posts()

            assert posts == []

    @patch("platforms.twitter.Config")
    @patch("platforms.twitter.TWEEPY_AVAILABLE", True)
    def test_get_recent_posts_handles_exception(self, mock_config):
        """Test get_recent_posts handles exceptions gracefully."""
        mock_config.validate_twitter.return_value = True
        mock_config.TWITTER_BEARER_TOKEN = "bearer"
        mock_config.TWITTER_API_KEY = "key"
        mock_config.TWITTER_API_SECRET = "secret"
        mock_config.TWITTER_ACCESS_TOKEN = "token"
        mock_config.TWITTER_ACCESS_SECRET = "secret"

        with patch("platforms.twitter.tweepy") as mock_tweepy:
            mock_client = Mock()
            mock_client.get_me.side_effect = Exception("API Error")
            mock_tweepy.Client.return_value = mock_client

            from platforms.twitter import TwitterPlatform
            platform = TwitterPlatform()
            posts = platform.get_recent_posts()

            assert posts == []


class TestTwitterHealthCheck:
    """Tests for TwitterPlatform.health_check() method."""

    @patch("platforms.twitter.Config")
    def test_health_check_without_client(self, mock_config):
        """Test health_check returns False without client."""
        mock_config.validate_twitter.return_value = False

        from platforms.twitter import TwitterPlatform
        platform = TwitterPlatform()
        result = platform.health_check()

        assert result is False

    @patch("platforms.twitter.Config")
    @patch("platforms.twitter.TWEEPY_AVAILABLE", True)
    def test_health_check_success(self, mock_config):
        """Test health_check returns True with valid credentials."""
        mock_config.validate_twitter.return_value = True
        mock_config.TWITTER_BEARER_TOKEN = "bearer"
        mock_config.TWITTER_API_KEY = "key"
        mock_config.TWITTER_API_SECRET = "secret"
        mock_config.TWITTER_ACCESS_TOKEN = "token"
        mock_config.TWITTER_ACCESS_SECRET = "secret"

        with patch("platforms.twitter.tweepy") as mock_tweepy:
            mock_client = Mock()
            mock_me = Mock()
            mock_me.data = Mock(id="user123")
            mock_client.get_me.return_value = mock_me
            mock_tweepy.Client.return_value = mock_client

            from platforms.twitter import TwitterPlatform
            platform = TwitterPlatform()
            result = platform.health_check()

            assert result is True

    @patch("platforms.twitter.Config")
    @patch("platforms.twitter.TWEEPY_AVAILABLE", True)
    def test_health_check_failure(self, mock_config):
        """Test health_check returns False when get_me fails."""
        mock_config.validate_twitter.return_value = True
        mock_config.TWITTER_BEARER_TOKEN = "bearer"
        mock_config.TWITTER_API_KEY = "key"
        mock_config.TWITTER_API_SECRET = "secret"
        mock_config.TWITTER_ACCESS_TOKEN = "token"
        mock_config.TWITTER_ACCESS_SECRET = "secret"

        with patch("platforms.twitter.tweepy") as mock_tweepy:
            mock_client = Mock()
            mock_client.get_me.side_effect = Exception("Unauthorized")
            mock_tweepy.Client.return_value = mock_client

            from platforms.twitter import TwitterPlatform
            platform = TwitterPlatform()
            result = platform.health_check()

            assert result is False


class TestTwitterPlatformProperties:
    """Tests for TwitterPlatform properties."""

    def test_platform_name(self):
        """Test platform name is 'twitter'."""
        with patch("platforms.twitter.Config") as mock_config:
            mock_config.validate_twitter.return_value = False
            from platforms.twitter import TwitterPlatform
            platform = TwitterPlatform()
            assert platform.name == "twitter"

    def test_max_length(self):
        """Test max length is 280."""
        with patch("platforms.twitter.Config") as mock_config:
            mock_config.validate_twitter.return_value = False
            from platforms.twitter import TwitterPlatform
            platform = TwitterPlatform()
            assert platform.max_length == 280
