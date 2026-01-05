"""Tool for composing social media posts."""

import logging
from typing import Dict, Any

from .base import BaseTool

logger = logging.getLogger(__name__)


class ComposePostTool(BaseTool):
    """Compose a platform-agnostic social media post from analysis."""

    name = "compose_post"
    description = "Compose a social media post from options analysis results. Adapts format to target platform."

    def get_schema(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "symbol": {
                        "type": "string",
                        "description": "Stock symbol (e.g., AAPL)"
                    },
                    "strategy": {
                        "type": "string",
                        "description": "Options strategy (e.g., Covered Call, Iron Condor)"
                    },
                    "thesis": {
                        "type": "string",
                        "description": "Investment thesis with specific catalyst details. Use suggestive language (could, might, potential)."
                    },
                    "strike": {
                        "type": "string",
                        "description": "Strike price info (e.g., '$280 (3% OTM)')"
                    },
                    "expiration": {
                        "type": "string",
                        "description": "Expiration date (e.g., 'Jan 30')"
                    },
                    "premium": {
                        "type": "string",
                        "description": "Premium amount (e.g., '$4.50')"
                    },
                    "pop": {
                        "type": "string",
                        "description": "Probability of profit (e.g., '68%')"
                    },
                    "why_now": {
                        "type": "string",
                        "description": "Brief explanation of timing rationale"
                    },
                    "platform": {
                        "type": "string",
                        "enum": ["twitter", "threads", "discord"],
                        "description": "Target platform to adapt format"
                    }
                },
                "required": ["symbol", "strategy", "thesis", "platform"]
            }
        }

    def execute(
        self,
        symbol: str,
        strategy: str,
        thesis: str,
        platform: str,
        strike: str = "",
        expiration: str = "",
        premium: str = "",
        pop: str = "",
        why_now: str = ""
    ) -> str:
        """Compose a post for the target platform."""

        # Use softer header - not "Alert" which sounds too certain
        header = "Trade Idea"

        # Platform-specific formatting
        if platform == "twitter":
            return self._format_twitter(
                header, symbol, strategy, thesis, strike, expiration, premium, pop, why_now
            )
        elif platform == "threads":
            return self._format_threads(
                header, symbol, strategy, thesis, strike, expiration, premium, pop, why_now
            )
        else:
            return self._format_twitter(
                header, symbol, strategy, thesis, strike, expiration, premium, pop, why_now
            )

    def _format_twitter(
        self, header: str, symbol: str, strategy: str, thesis: str,
        strike: str, expiration: str, premium: str, pop: str, why_now: str
    ) -> str:
        """Format for Twitter (280 char limit)."""
        tweet_parts = []

        # Lead with thesis (no header - more engaging)
        if thesis:
            tweet_parts.append(thesis)
            tweet_parts.append("")

        # Symbol and strategy
        tweet_parts.append(f"${symbol} {strategy}")

        # Compact metrics on one line
        metrics = []
        if strike:
            metrics.append(strike)
        if expiration:
            metrics.append(f"{expiration} exp")
        if metrics:
            tweet_parts.append(" | ".join(metrics))

        # Stats on one line
        stats = []
        if premium:
            stats.append(f"{premium} premium")
        if pop:
            stats.append(f"{pop} POP")
        if stats:
            tweet_parts.append(" | ".join(stats))

        # Add "Why" context if provided
        if why_now:
            tweet_parts.append("")
            tweet_parts.append(f"Why: {why_now[:80]}")

        # Hashtags
        tweet_parts.append("")
        hashtags = f"#{symbol} #options #NFA"
        tweet_parts.append(hashtags)

        composed = "\n".join(tweet_parts)

        # Truncate thesis if too long
        if len(composed) > 280 and thesis:
            max_thesis_len = len(thesis) - (len(composed) - 280) - 3
            if max_thesis_len > 20:
                thesis = thesis[:max_thesis_len] + "..."
                return self._format_twitter(header, symbol, strategy, thesis, strike, expiration, premium, pop, why_now)

        return f"COMPOSED_POST:\n{composed}\n\nCHARACTER_COUNT: {len(composed)}"

    def _format_threads(
        self, header: str, symbol: str, strategy: str, thesis: str,
        strike: str, expiration: str, premium: str, pop: str, why_now: str
    ) -> str:
        """Format for Threads (500 char limit, more room for detail)."""
        post_parts = []

        # Lead with thesis (no header)
        if thesis:
            post_parts.append(thesis)
            post_parts.append("")

        post_parts.append(f"${symbol} {strategy}")
        post_parts.append("")

        if strike:
            post_parts.append(f"Strike: {strike}")
        if expiration:
            post_parts.append(f"Exp: {expiration}")
        if premium:
            post_parts.append(f"Premium: {premium}")
        if pop:
            post_parts.append(f"POP: {pop}")

        if why_now:
            post_parts.append("")
            post_parts.append(f"Why: {why_now[:200]}")

        post_parts.append("")
        post_parts.append(f"#{symbol} #options #NFA")

        composed = "\n".join(post_parts)

        return f"COMPOSED_POST:\n{composed}\n\nCHARACTER_COUNT: {len(composed)}"
