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
                        "description": "Investment thesis - the story/catalyst driving this trade (e.g., 'NVDA surging on new AI chip announcement')"
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

        header = "Options Alert"

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
        # Build metrics line
        metrics_parts = []
        if strike:
            metrics_parts.append(strike)
        if expiration:
            metrics_parts.append(f"Exp: {expiration}")
        metrics_line = " | ".join(metrics_parts) if metrics_parts else ""

        stats_parts = []
        if premium:
            stats_parts.append(f"Premium: {premium}")
        if pop:
            stats_parts.append(f"POP: {pop}")
        stats_line = " | ".join(stats_parts) if stats_parts else ""

        # Build tweet with thesis at top
        tweet_parts = [header, ""]

        # Add thesis (the story)
        if thesis:
            tweet_parts.append(thesis)
            tweet_parts.append("")

        tweet_parts.append(f"${symbol} {strategy}")

        if metrics_line:
            tweet_parts.append(metrics_line)
        if stats_line:
            tweet_parts.append(stats_line)

        # Add symbol-specific hashtag
        hashtags = f"#{symbol} #options"

        # Calculate remaining space
        base = "\n".join(tweet_parts)
        full = base + "\n" + hashtags

        # Truncate thesis if needed to fit
        if len(full) > 280 and thesis:
            max_thesis_len = 280 - (len(full) - len(thesis)) - 3
            if max_thesis_len > 20:
                thesis = thesis[:max_thesis_len] + "..."
                # Rebuild tweet
                tweet_parts = [header, "", thesis, "", f"${symbol} {strategy}"]
                if metrics_line:
                    tweet_parts.append(metrics_line)
                if stats_line:
                    tweet_parts.append(stats_line)

        tweet_parts.append(hashtags)
        composed = "\n".join(tweet_parts)

        return f"COMPOSED_POST:\n{composed}\n\nCHARACTER_COUNT: {len(composed)}"

    def _format_threads(
        self, header: str, symbol: str, strategy: str, thesis: str,
        strike: str, expiration: str, premium: str, pop: str, why_now: str
    ) -> str:
        """Format for Threads (500 char limit, more room for detail)."""
        post_parts = [
            f"{header}",
            ""
        ]

        # Add thesis at top (the story)
        if thesis:
            post_parts.append(thesis)
            post_parts.append("")

        post_parts.append(f"${symbol} {strategy}")
        post_parts.append("")

        if strike:
            post_parts.append(f"Strike: {strike}")
        if expiration:
            post_parts.append(f"Expiration: {expiration}")
        if premium:
            post_parts.append(f"Premium: {premium}")
        if pop:
            post_parts.append(f"Probability of Profit: {pop}")

        if why_now:
            post_parts.append("")
            post_parts.append(why_now[:200])

        post_parts.append("")
        post_parts.append(f"#{symbol} #options #trading")

        composed = "\n".join(post_parts)

        return f"COMPOSED_POST:\n{composed}\n\nCHARACTER_COUNT: {len(composed)}"
