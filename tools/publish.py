"""Tool for publishing to social media platforms."""

import logging
from typing import Dict, Any, List

from .base import BaseTool
from platforms.twitter import TwitterPlatform
from platforms.threads import ThreadsPlatform
from agent.config import Config

logger = logging.getLogger(__name__)

# Platform registry
PLATFORMS = {
    "twitter": TwitterPlatform,
    "threads": ThreadsPlatform,
}

# Promotional messages for Alpha Copilot
PROMO_MESSAGES = {
    "twitter": (
        "🚀 Want more options insights like this? "
        "Alpha Copilot uses AI to find high-probability trades tailored to your risk profile. "
        f"Try it free: {{url}} #AlphaCopilot #OptionsTrading"
    ),
    "threads": (
        "🚀 Want more options insights like this?\n\n"
        "Alpha Copilot uses AI to analyze thousands of options contracts "
        "and find high-probability trades tailored to your risk profile.\n\n"
        "✅ Income strategies (covered calls, cash-secured puts)\n"
        "✅ Real-time market analysis\n"
        "✅ Personalized recommendations\n\n"
        "Try it free: {url}\n\n"
        "#AlphaCopilot #OptionsTrading #FinTech"
    ),
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


class CrossPostTool(BaseTool):
    """Cross-post content to multiple platforms (Twitter + Threads) with promotional follow-up."""

    name = "cross_post"
    description = (
        "Post content to both Twitter and Threads simultaneously. "
        "Automatically adds a promotional follow-up post for Alpha Copilot if enabled."
    )

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
                        "description": "The main content to publish to both platforms"
                    },
                    "include_promo": {
                        "type": "boolean",
                        "description": "Whether to post a promotional follow-up (default: true if ENABLE_PROMO_POST is set)"
                    }
                },
                "required": ["content"]
            }
        }

    def _get_platform(self, platform_name: str):
        """Get or create platform instance."""
        if platform_name not in self._platform_instances:
            if platform_name not in PLATFORMS:
                return None
            self._platform_instances[platform_name] = PLATFORMS[platform_name]()
        return self._platform_instances[platform_name]

    def _format_content_for_platform(self, content: str, platform_name: str) -> str:
        """Adjust content formatting for specific platform limits."""
        platform = self._get_platform(platform_name)
        if platform:
            return platform.truncate_content(content)
        return content

    def _get_promo_message(self, platform_name: str) -> str:
        """Get the promotional message for a specific platform."""
        template = PROMO_MESSAGES.get(platform_name, PROMO_MESSAGES["twitter"])
        return template.format(url=Config.ALPHA_COPILOT_URL)

    def execute(self, content: str, include_promo: bool = None) -> str:
        """Cross-post content to Twitter and Threads with optional promo."""
        # Determine if we should include promo
        if include_promo is None:
            include_promo = Config.ENABLE_PROMO_POST

        results: List[str] = []
        platforms_to_post = ["twitter", "threads"]

        # Post main content to both platforms
        for platform_name in platforms_to_post:
            platform = self._get_platform(platform_name)

            if not platform:
                results.append(f"SKIPPED: {platform_name} - not configured")
                continue

            # Format content for platform
            formatted_content = self._format_content_for_platform(content, platform_name)

            logger.info(f"Cross-posting to {platform_name}: {formatted_content[:50]}...")
            result = platform.publish(formatted_content)

            if result.get("success"):
                post_id = result.get("post_id", "unknown")
                url = result.get("url", "")
                dry_run = result.get("dry_run", False)

                if dry_run:
                    results.append(f"DRY_RUN: {platform_name} - would have posted")
                else:
                    results.append(f"SUCCESS: {platform_name} - Post ID: {post_id}, URL: {url}")

                # Post promotional follow-up if enabled
                if include_promo and not dry_run:
                    promo_content = self._get_promo_message(platform_name)
                    promo_result = platform.publish(promo_content)

                    if promo_result.get("success"):
                        promo_id = promo_result.get("post_id", "unknown")
                        promo_url = promo_result.get("url", "")
                        results.append(f"PROMO: {platform_name} - Post ID: {promo_id}, URL: {promo_url}")
                    else:
                        promo_error = promo_result.get("error", "Unknown error")
                        results.append(f"PROMO_FAILED: {platform_name} - {promo_error}")
                elif include_promo and dry_run:
                    results.append(f"DRY_RUN: {platform_name} promo - would have posted")
            else:
                error = result.get("error", "Unknown error")
                results.append(f"FAILED: {platform_name} - {error}")

        return "CROSS_POST_RESULTS:\n" + "\n".join(results)


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
