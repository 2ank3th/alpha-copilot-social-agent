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

    def publish(self, content: str, reply_to_id: str = None) -> Dict[str, Any]:
        """Publish a tweet, optionally as a reply to create a thread."""
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

            # Create tweet, optionally as reply to form a thread
            if reply_to_id:
                response = self._client.create_tweet(
                    text=content,
                    in_reply_to_tweet_id=reply_to_id
                )
            else:
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
        """Get recent tweets from authenticated user.

        Note: Disabled - requires Twitter read access which is not available.
        Returns empty list to allow agent to proceed without duplicate checking.
        """
        # Read access not available - return empty to skip duplicate check
        logger.info("Twitter read access not available - skipping recent posts check")
        return []

    def health_check(self) -> bool:
        """Check if Twitter credentials are configured.

        Note: Only checks if credentials are set, does not validate via API
        since read access is not available.
        """
        # Just check if client is initialized (credentials are set)
        return self._client is not None
