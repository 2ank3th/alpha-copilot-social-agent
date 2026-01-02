"""Twitter/X platform adapter."""

import logging
from typing import Dict, List, Any

try:
    import tweepy
    TWEEPY_AVAILABLE = True
except ImportError:
    TWEEPY_AVAILABLE = False

from .base import BasePlatform
from agent.config import Config

logger = logging.getLogger(__name__)


class TwitterPlatform(BasePlatform):
    """Twitter/X platform adapter using Tweepy."""

    name = "twitter"
    max_length = 280

    def __init__(self):
        self._client = None
        if TWEEPY_AVAILABLE and Config.validate_twitter():
            self._client = tweepy.Client(
                bearer_token=Config.TWITTER_BEARER_TOKEN or None,
                consumer_key=Config.TWITTER_API_KEY,
                consumer_secret=Config.TWITTER_API_SECRET,
                access_token=Config.TWITTER_ACCESS_TOKEN,
                access_token_secret=Config.TWITTER_ACCESS_SECRET
            )

    def publish(self, content: str) -> Dict[str, Any]:
        """Publish a tweet."""
        if Config.DRY_RUN:
            logger.info(f"[DRY RUN] Would tweet: {content[:50]}...")
            return {
                "success": True,
                "post_id": "dry_run_id",
                "url": "https://twitter.com/dry_run",
                "dry_run": True
            }

        if not self._client:
            return {
                "success": False,
                "error": "Twitter client not initialized. Check credentials."
            }

        try:
            # Truncate to max length
            content = self.truncate_content(content)

            response = self._client.create_tweet(text=content)
            tweet_id = response.data["id"]

            return {
                "success": True,
                "post_id": tweet_id,
                "url": f"https://twitter.com/i/status/{tweet_id}"
            }
        except Exception as e:
            logger.error(f"Failed to post tweet: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    def get_recent_posts(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Get recent tweets from authenticated user."""
        if not self._client:
            return []

        try:
            # Get authenticated user
            me = self._client.get_me()
            if not me.data:
                return []

            # Get recent tweets
            tweets = self._client.get_users_tweets(
                me.data.id,
                max_results=10,
                tweet_fields=["created_at", "text"]
            )

            if not tweets.data:
                return []

            return [
                {
                    "id": str(tweet.id),
                    "content": tweet.text,
                    "created_at": tweet.created_at.isoformat() if tweet.created_at else None
                }
                for tweet in tweets.data
            ]
        except Exception as e:
            logger.warning(f"Failed to get recent tweets: {e}")
            return []

    def health_check(self) -> bool:
        """Check if Twitter credentials are valid."""
        if not self._client:
            return False

        try:
            me = self._client.get_me()
            return me.data is not None
        except Exception as e:
            logger.warning(f"Twitter health check failed: {e}")
            return False
