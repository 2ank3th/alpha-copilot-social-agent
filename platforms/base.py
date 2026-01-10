"""Base class for platform adapters."""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional


class BasePlatform(ABC):
    """Abstract base class for social media platform adapters."""

    name: str
    max_length: int  # Character limit for posts

    @abstractmethod
    def publish(self, content: str, reply_to_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Publish content to the platform.

        Args:
            content: The text content to publish
            reply_to_id: Optional ID of post to reply to (for threading)

        Returns:
            Dict with 'success', 'post_id', 'url', and optionally 'error'
        """
        pass

    @abstractmethod
    def get_recent_posts(self, hours: int = 24) -> List[Dict[str, Any]]:
        """
        Get recent posts from this platform.

        Args:
            hours: How far back to look (default 24 hours)

        Returns:
            List of post dicts with 'id', 'content', 'created_at'
        """
        pass

    @abstractmethod
    def health_check(self) -> bool:
        """
        Check if platform credentials are valid and API is accessible.

        Returns:
            True if platform is ready to use
        """
        pass

    def truncate_content(self, content: str) -> str:
        """Truncate content to platform's max length."""
        if len(content) <= self.max_length:
            return content
        return content[:self.max_length - 3] + "..."

    def __repr__(self) -> str:
        return f"<Platform: {self.name} (max {self.max_length} chars)>"
