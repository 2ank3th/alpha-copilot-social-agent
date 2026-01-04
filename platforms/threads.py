"""Threads platform adapter using Meta's Threads API."""

import logging
import time
from typing import Dict, List, Any

import httpx

from .base import BasePlatform
from agent.config import Config

logger = logging.getLogger(__name__)


class ThreadsPlatform(BasePlatform):
    """Threads platform adapter using Meta's Graph API for Threads."""

    name = "threads"
    max_length = 500  # Threads allows up to 500 characters

    # Meta Graph API base URL for Threads
    API_BASE = "https://graph.threads.net/v1.0"

    def __init__(self):
        self._access_token = Config.THREADS_ACCESS_TOKEN
        self._user_id = Config.THREADS_USER_ID
        self._client = httpx.Client(timeout=30)

    @property
    def _is_configured(self) -> bool:
        """Check if Threads credentials are configured."""
        return bool(self._access_token and self._user_id)

    def _create_container(self, content: str) -> str | None:
        """
        Create a media container for the Threads post.

        Returns the container ID if successful, None otherwise.
        """
        url = f"{self.API_BASE}/{self._user_id}/threads"
        params = {
            "media_type": "TEXT",
            "text": content,
            "access_token": self._access_token,
        }

        try:
            response = self._client.post(url, params=params)
            response.raise_for_status()
            data = response.json()
            return data.get("id")
        except Exception as e:
            logger.error(f"Failed to create Threads container: {e}")
            return None

    def _publish_container(self, container_id: str) -> Dict[str, Any]:
        """
        Publish a media container to Threads.

        Returns post data if successful.
        """
        url = f"{self.API_BASE}/{self._user_id}/threads_publish"
        params = {
            "creation_id": container_id,
            "access_token": self._access_token,
        }

        try:
            response = self._client.post(url, params=params)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to publish Threads container: {e}")
            return {"error": str(e)}

    def publish(self, content: str) -> Dict[str, Any]:
        """Publish a post to Threads."""
        if Config.DRY_RUN:
            logger.info(f"[DRY RUN] Would post to Threads: {content[:50]}...")
            return {
                "success": True,
                "post_id": "dry_run_threads_id",
                "url": "https://threads.net/dry_run",
                "dry_run": True
            }

        if not self._is_configured:
            return {
                "success": False,
                "error": "Threads credentials not configured. Check THREADS_ACCESS_TOKEN and THREADS_USER_ID."
            }

        try:
            # Truncate to max length
            content = self.truncate_content(content)

            # Step 1: Create media container
            container_id = self._create_container(content)
            if not container_id:
                return {
                    "success": False,
                    "error": "Failed to create Threads media container"
                }

            # Step 2: Wait briefly for container to be ready (API requirement)
            time.sleep(1)

            # Step 3: Publish the container
            result = self._publish_container(container_id)

            if "error" in result:
                return {
                    "success": False,
                    "error": result["error"]
                }

            post_id = result.get("id", container_id)

            return {
                "success": True,
                "post_id": post_id,
                "url": f"https://www.threads.net/post/{post_id}"
            }

        except Exception as e:
            logger.error(f"Failed to post to Threads: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    def get_recent_posts(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Get recent posts from the authenticated Threads user."""
        if not self._is_configured:
            return []

        try:
            url = f"{self.API_BASE}/{self._user_id}/threads"
            params = {
                "fields": "id,text,timestamp",
                "limit": 10,
                "access_token": self._access_token,
            }

            response = self._client.get(url, params=params)
            response.raise_for_status()
            data = response.json()

            posts = data.get("data", [])
            return [
                {
                    "id": post.get("id", ""),
                    "content": post.get("text", ""),
                    "created_at": post.get("timestamp", "")
                }
                for post in posts
            ]

        except Exception as e:
            logger.warning(f"Failed to get recent Threads posts: {e}")
            return []

    def health_check(self) -> bool:
        """Check if Threads credentials are valid."""
        if not self._is_configured:
            return False

        try:
            url = f"{self.API_BASE}/me"
            params = {
                "fields": "id,username",
                "access_token": self._access_token,
            }

            response = self._client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            return "id" in data

        except Exception as e:
            logger.warning(f"Threads health check failed: {e}")
            return False

    def __del__(self):
        """Clean up HTTP client."""
        if hasattr(self, "_client"):
            self._client.close()
