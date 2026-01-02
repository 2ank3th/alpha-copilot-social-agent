"""Tool for publishing to social media platforms."""

import logging
from typing import Dict, Any

from .base import BaseTool
from platforms.twitter import TwitterPlatform

logger = logging.getLogger(__name__)

# Platform registry
PLATFORMS = {
    "twitter": TwitterPlatform,
}


class PublishTool(BaseTool):
    """Publish content to a social media platform."""

    name = "publish"
    description = "Publish content to a social media platform (twitter, threads, discord)."

    def __init__(self):
        self._platform_instances = {}

    def get_schema(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "content": {
                        "type": "string",
                        "description": "The content to publish"
                    },
                    "platform": {
                        "type": "string",
                        "enum": ["twitter", "threads", "discord"],
                        "description": "Target platform"
                    }
                },
                "required": ["content", "platform"]
            }
        }

    def _get_platform(self, platform_name: str):
        """Get or create platform instance."""
        if platform_name not in self._platform_instances:
            if platform_name not in PLATFORMS:
                return None
            self._platform_instances[platform_name] = PLATFORMS[platform_name]()
        return self._platform_instances[platform_name]

    def execute(self, content: str, platform: str) -> str:
        """Publish content to the specified platform."""
        logger.info(f"Publishing to {platform}: {content[:50]}...")

        platform_adapter = self._get_platform(platform)

        if not platform_adapter:
            return f"ERROR: Platform '{platform}' is not supported. Available: {list(PLATFORMS.keys())}"

        result = platform_adapter.publish(content)

        if result.get("success"):
            post_id = result.get("post_id", "unknown")
            url = result.get("url", "")
            dry_run = result.get("dry_run", False)

            if dry_run:
                return f"DRY_RUN: Would have published to {platform}. Content: {content[:100]}..."
            else:
                return f"SUCCESS: Published to {platform}. Post ID: {post_id}. URL: {url}"
        else:
            error = result.get("error", "Unknown error")
            return f"ERROR: Failed to publish to {platform}. Error: {error}"


class CheckRecentPostsTool(BaseTool):
    """Check recent posts to avoid duplicates."""

    name = "check_recent_posts"
    description = "Check recent posts on a platform to avoid posting duplicate content."

    def __init__(self):
        self._platform_instances = {}

    def get_schema(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "platform": {
                        "type": "string",
                        "enum": ["twitter", "threads", "discord"],
                        "description": "Platform to check"
                    },
                    "hours": {
                        "type": "integer",
                        "description": "How many hours back to check (default: 24)"
                    }
                },
                "required": ["platform"]
            }
        }

    def _get_platform(self, platform_name: str):
        """Get or create platform instance."""
        if platform_name not in self._platform_instances:
            if platform_name not in PLATFORMS:
                return None
            self._platform_instances[platform_name] = PLATFORMS[platform_name]()
        return self._platform_instances[platform_name]

    def execute(self, platform: str, hours: int = 24) -> str:
        """Get recent posts from the platform."""
        platform_adapter = self._get_platform(platform)

        if not platform_adapter:
            return f"ERROR: Platform '{platform}' is not supported."

        posts = platform_adapter.get_recent_posts(hours)

        if not posts:
            return f"NO_RECENT_POSTS: No posts found on {platform} in the last {hours} hours."

        result_parts = [f"RECENT_POSTS on {platform} (last {hours} hours):"]
        for i, post in enumerate(posts[:5], 1):
            content = post.get("content", "")[:100]
            created = post.get("created_at", "unknown")
            result_parts.append(f"{i}. [{created}] {content}...")

        return "\n".join(result_parts)


class GetPlatformStatusTool(BaseTool):
    """Check if a platform is available and configured."""

    name = "get_platform_status"
    description = "Check if a platform is available and properly configured."

    def __init__(self):
        self._platform_instances = {}

    def get_schema(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "platform": {
                        "type": "string",
                        "enum": ["twitter", "threads", "discord"],
                        "description": "Platform to check"
                    }
                },
                "required": ["platform"]
            }
        }

    def _get_platform(self, platform_name: str):
        """Get or create platform instance."""
        if platform_name not in self._platform_instances:
            if platform_name not in PLATFORMS:
                return None
            self._platform_instances[platform_name] = PLATFORMS[platform_name]()
        return self._platform_instances[platform_name]

    def execute(self, platform: str) -> str:
        """Check platform status."""
        platform_adapter = self._get_platform(platform)

        if not platform_adapter:
            return f"UNAVAILABLE: Platform '{platform}' is not implemented yet."

        is_healthy = platform_adapter.health_check()

        if is_healthy:
            return f"AVAILABLE: {platform} is configured and ready to use."
        else:
            return f"UNAVAILABLE: {platform} credentials are not configured or invalid."


class DoneTool(BaseTool):
    """Signal that the task is complete."""

    name = "done"
    description = "Signal that the task is complete and provide a summary."

    def get_schema(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "summary": {
                        "type": "string",
                        "description": "Summary of what was accomplished"
                    }
                },
                "required": ["summary"]
            }
        }

    def execute(self, summary: str) -> str:
        """Return completion signal."""
        return f"TASK_COMPLETE: {summary}"
