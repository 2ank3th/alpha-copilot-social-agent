"""Tool for publishing to social media platforms."""

import hashlib
import json
import logging
import os
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, Any, List, Tuple
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

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

# Promotional messages for Alpha Copilot (posted as reply thread)
PROMO_MESSAGES = {
    "twitter": (
        "Want a live setup scanner for {ticker}?\n\n"
        "Alpha Copilot finds high-probability options ideas tailored to your risk profile.\n\n"
        "Try it free: {url}"
    ),
    "threads": (
        "Want a live setup scanner for {ticker}?\n\n"
        "Alpha Copilot uses AI to analyze thousands of options contracts "
        "and find high-probability trades tailored to your risk profile.\n\n"
        "✅ Income strategies (covered calls, cash-secured puts)\n"
        "✅ Real-time market analysis\n"
        "✅ Personalized recommendations\n\n"
        "Try it free: {url}"
    ),
}

# Variant pool to avoid repetitive promo copy and support lightweight A/B testing.
PROMO_MESSAGE_VARIANTS = {
    "twitter": [
        (
            "If you're tracking {ticker}, you can scan fresh setups in seconds.\n\n"
            "Alpha Copilot ranks high-probability ideas by risk profile.\n\n"
            "Try it free: {url}"
        ),
        (
            "Curious what trade scores best on {ticker} right now?\n\n"
            "Alpha Copilot runs the screen instantly and explains the setup.\n\n"
            "Start free: {url}"
        ),
        (
            "I use Alpha Copilot to pressure-test ideas like {ticker} before entry.\n\n"
            "You can run the same workflow free: {url}"
        ),
    ],
    "threads": [
        (
            "If you're tracking {ticker}, this can help:\n\n"
            "Alpha Copilot scans the chain, ranks probability, and suggests entries by risk profile.\n\n"
            "Try it free: {url}"
        ),
        (
            "Want more than one trade idea on {ticker}?\n\n"
            "Alpha Copilot surfaces multiple setups (income + directional) and the rationale behind each one.\n\n"
            "Start free: {url}"
        ),
        (
            "Need a faster way to go from headline to trade on {ticker}?\n\n"
            "Alpha Copilot turns market moves into actionable options setups in seconds.\n\n"
            "Try it free: {url}"
        ),
    ],
}

MAX_POST_HISTORY_ENTRIES = 500


def _history_file_path() -> Path:
    """Get normalized local history file path."""
    return Path(Config.POST_HISTORY_PATH).expanduser()


def _load_post_history() -> List[Dict[str, Any]]:
    """Load locally cached post history."""
    history_path = _history_file_path()
    if not history_path.exists():
        return []

    try:
        raw_data = json.loads(history_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        logger.warning("Could not read post history file: %s", history_path)
        return []

    if not isinstance(raw_data, list):
        return []

    return [entry for entry in raw_data if isinstance(entry, dict)]


def _save_post_history(entries: List[Dict[str, Any]]) -> None:
    """Persist local post history to disk."""
    history_path = _history_file_path()

    try:
        history_path.parent.mkdir(parents=True, exist_ok=True)
        history_path.write_text(
            json.dumps(entries[-MAX_POST_HISTORY_ENTRIES:], indent=2),
            encoding="utf-8",
        )
    except OSError:
        logger.warning("Could not persist post history file: %s", history_path)


def _record_post_history(
    platform: str,
    content: str,
    post_id: str = "",
    url: str = "",
    is_promo: bool = False,
) -> None:
    """Record a published post locally for duplicate detection."""
    history = _load_post_history()
    history.append(
        {
            "platform": platform,
            "post_id": post_id,
            "url": url,
            "content": content,
            "is_promo": is_promo,
            "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        }
    )
    _save_post_history(history)


def _get_recent_local_posts(platform: str, hours: int) -> List[Dict[str, Any]]:
    """Fetch recent posts from local history cache."""
    cutoff = datetime.now(timezone.utc) - timedelta(hours=max(1, hours))
    history = _load_post_history()

    recent_posts: List[Dict[str, Any]] = []
    for entry in reversed(history):
        if entry.get("platform") != platform:
            continue
        if entry.get("is_promo"):
            continue

        created_at = entry.get("created_at", "")
        try:
            created_dt = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
        except ValueError:
            continue

        if created_dt < cutoff:
            continue

        recent_posts.append(
            {
                "id": entry.get("post_id", ""),
                "content": entry.get("content", ""),
                "created_at": created_at,
            }
        )

        if len(recent_posts) >= 20:
            break

    return recent_posts


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
                if not Config.DRY_RUN:
                    _record_post_history(
                        platform=platform,
                        content=content,
                        post_id=post_id,
                        url=url,
                        is_promo=False,
                    )
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
            posts = _get_recent_local_posts(platform=platform, hours=hours)

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
                    },
                    "image_path": {
                        "type": "string",
                        "description": "Optional path to a trade card image to attach to the post"
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

    def _extract_primary_ticker(self, content: str) -> str:
        """Extract first ticker symbol from post content for message personalization."""
        match = re.search(r"\$([A-Z]{1,5})\b", content)
        if not match:
            return "this setup"
        return f"${match.group(1)}"

    def _select_promo_template(self, platform_name: str, content: str) -> Tuple[int, str]:
        """Select a deterministic promo variant to avoid repetitive copy."""
        variants = PROMO_MESSAGE_VARIANTS.get(platform_name)
        if not variants:
            fallback = PROMO_MESSAGES.get(platform_name, PROMO_MESSAGES["twitter"])
            return 0, fallback

        digest = hashlib.sha1(f"{platform_name}:{content}".encode("utf-8")).hexdigest()
        variant_index = int(digest[:8], 16) % len(variants)
        return variant_index, variants[variant_index]

    def _build_tracking_url(self, platform_name: str, variant_index: int) -> str:
        """Build promo URL with UTM tags for channel and variant attribution."""
        parsed = urlparse(Config.ALPHA_COPILOT_URL)
        query_params = dict(parse_qsl(parsed.query, keep_blank_values=True))
        query_params.update({
            "utm_source": platform_name,
            "utm_medium": Config.ALPHA_COPILOT_UTM_MEDIUM,
            "utm_campaign": Config.ALPHA_COPILOT_UTM_CAMPAIGN,
            "utm_content": f"{Config.ALPHA_COPILOT_UTM_CONTENT_PREFIX}-v{variant_index + 1}",
        })

        return urlunparse(parsed._replace(query=urlencode(query_params)))

    def _get_promo_message(self, platform_name: str, content: str) -> Tuple[str, int]:
        """Get platform-specific promotional message and selected variant number."""
        variant_index, template = self._select_promo_template(platform_name, content)
        promo_url = self._build_tracking_url(platform_name, variant_index)
        ticker = self._extract_primary_ticker(content)

        try:
            message = template.format(url=promo_url, ticker=ticker)
        except KeyError:
            # Defensive fallback for malformed templates.
            message = PROMO_MESSAGES.get(platform_name, PROMO_MESSAGES["twitter"]).format(
                url=promo_url,
                ticker=ticker,
            )

        return message, variant_index + 1

    def execute(self, content: str, include_promo: bool = None, image_path: str = None) -> str:
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

            # Upload image if provided (Twitter only for now)
            media_ids = None
            if image_path and platform_name == "twitter":
                try:
                    if hasattr(platform, 'upload_media'):
                        media_id = platform.upload_media(image_path)
                        media_ids = [media_id]
                        logger.info(f"Uploaded image for {platform_name}: {media_id}")
                except Exception as e:
                    logger.warning(f"Image upload failed for {platform_name}, posting text-only: {e}")

            logger.info(f"Cross-posting to {platform_name}: {formatted_content[:50]}...")
            result = platform.publish(formatted_content, media_ids=media_ids)

            if result.get("success"):
                post_id = result.get("post_id", "unknown")
                url = result.get("url", "")
                dry_run = result.get("dry_run", False)

                if dry_run:
                    results.append(f"DRY_RUN: {platform_name} - would have posted")
                else:
                    results.append(f"SUCCESS: {platform_name} - Post ID: {post_id}, URL: {url}")
                    if not Config.DRY_RUN:
                        _record_post_history(
                            platform=platform_name,
                            content=formatted_content,
                            post_id=post_id,
                            url=url,
                            is_promo=False,
                        )

                promo_content = ""
                promo_variant = 1
                if include_promo:
                    promo_content, promo_variant = self._get_promo_message(platform_name, formatted_content)
                    promo_content = self._format_content_for_platform(promo_content, platform_name)

                # Post promotional follow-up as reply thread if enabled
                if include_promo and not dry_run:
                    # Post promo as reply to main post (creates a thread)
                    promo_result = platform.publish(promo_content, reply_to_id=post_id)

                    if promo_result.get("success"):
                        promo_id = promo_result.get("post_id", "unknown")
                        promo_url = promo_result.get("url", "")
                        if not Config.DRY_RUN:
                            _record_post_history(
                                platform=platform_name,
                                content=promo_content,
                                post_id=promo_id,
                                url=promo_url,
                                is_promo=True,
                            )
                        results.append(
                            f"PROMO (thread): {platform_name} - Variant v{promo_variant}, "
                            f"Post ID: {promo_id}, URL: {promo_url}"
                        )
                    else:
                        promo_error = promo_result.get("error", "Unknown error")
                        results.append(f"PROMO_FAILED: {platform_name} (v{promo_variant}) - {promo_error}")
                elif include_promo and dry_run:
                    results.append(
                        f"DRY_RUN: {platform_name} promo thread (v{promo_variant}) - would have posted as reply"
                    )
            else:
                error = result.get("error", "Unknown error")
                results.append(f"FAILED: {platform_name} - {error}")

        # Clean up temp image file
        if image_path:
            try:
                os.remove(image_path)
                logger.info(f"Cleaned up temp image: {image_path}")
            except OSError:
                pass

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
