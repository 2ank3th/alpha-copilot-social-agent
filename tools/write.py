"""Tool for writing social media posts with LLM-generated content."""

import logging
import re
from typing import Dict, Any

from .base import BaseTool

logger = logging.getLogger(__name__)


class WritePostTool(BaseTool):
    """Write a complete social media post with full creative control."""

    name = "write_post"
    description = (
        "Write a complete, engaging social media post about an options trade. "
        "You have full creative control - write the ENTIRE post text from scratch. "
        "NO templates - use your own words to tell a compelling story that leads with NEWS."
    )

    def get_schema(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "post_text": {
                        "type": "string",
                        "description": (
                            "The COMPLETE post text. Write it exactly as it should appear. "
                            "Lead with the news hook, follow with the trade idea. "
                            "Include specific details (strike, premium, expiration, POP). "
                            "Make it sound human and engaging, not robotic."
                        )
                    },
                    "platform": {
                        "type": "string",
                        "enum": ["twitter", "threads"],
                        "description": "Target platform (for length validation)"
                    }
                },
                "required": ["post_text", "platform"]
            }
        }

    def execute(self, post_text: str, platform: str = "twitter") -> str:
        """
        Validate and prepare post text for publishing.

        Args:
            post_text: Complete post text written by LLM
            platform: Target platform for length validation

        Returns:
            Success message with character count, or error
        """
        # Platform length limits
        LIMITS = {
            "twitter": 280,
            "threads": 500,
        }

        limit = LIMITS.get(platform, 280)
        char_count = len(post_text)

        # Validation
        if char_count > limit:
            over_by = char_count - limit
            tips = []
            if "(Nvidia)" in post_text or "(Tesla)" in post_text or "(" in post_text:
                tips.append("Remove company name in parentheses")
            if "approximately" in post_text.lower():
                tips.append("Use '~' instead of 'approximately'")
            if " just " in post_text.lower():
                tips.append("Remove filler word 'just'")
            if "expiration" in post_text.lower() or "expiry" in post_text.lower():
                tips.append("Use 'exp' instead of 'expiration/expiry'")
            if len(tips) == 0:
                tips.append("Remove adjectives and shorten phrases")

            return (
                f"ERROR: Post too long for {platform}. "
                f"{char_count}/{limit} characters (over by {over_by}). "
                f"Tips to shorten: {', '.join(tips)}. "
                f"Be aggressive - cut anything non-essential!"
            )

        if char_count < 50:
            return (
                f"ERROR: Post too short ({char_count} chars). "
                "Add more context or details."
            )

        # Check for required elements (suggestive, not strict)
        has_ticker = bool(re.search(r'\$[A-Z]{1,5}\b', post_text))
        has_number = bool(re.search(r'\d', post_text))

        warnings = []
        if not has_ticker:
            warnings.append("WARNING: No ticker symbol ($SYMBOL) found")
        if not has_number:
            warnings.append("WARNING: No numbers found (strike/premium/date)")

        # Build response
        response_parts = [
            f"POST_READY: {char_count}/{limit} characters",
            f"Platform: {platform}",
            "",
            "POST TEXT:",
            post_text,
        ]

        if warnings:
            response_parts.extend(["", "SUGGESTIONS:"] + warnings)

        return "\n".join(response_parts)
