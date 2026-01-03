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
                        "description": "Brief explanation of why this is a good opportunity NOW"
                    },
                    "platform": {
                        "type": "string",
                        "enum": ["twitter", "threads", "discord"],
                        "description": "Target platform to adapt format"
                    }
                },
                "required": ["symbol", "strategy", "why_now", "platform"]
            }
        }

    def execute(
        self,
        symbol: str,
        strategy: str,
        why_now: str,
        platform: str,
        strike: str = "",
        expiration: str = "",
        premium: str = "",
        pop: str = ""
    ) -> str:
        """Compose a post for the target platform."""

        header = "Options Alert"

        # Platform-specific formatting
        if platform == "twitter":
            return self._format_twitter(
                header, symbol, strategy, strike, expiration, premium, pop, why_now
            )
        elif platform == "threads":
            return self._format_threads(
                header, symbol, strategy, strike, expiration, premium, pop, why_now
            )
        else:
            return self._format_twitter(
                header, symbol, strategy, strike, expiration, premium, pop, why_now
            )

    def _format_twitter(
        self, header: str, symbol: str, strategy: str,
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

        # Build tweet
        tweet_parts = [header, "", f"${symbol} {strategy}"]

        if metrics_line:
            tweet_parts.append(metrics_line)
        if stats_line:
            tweet_parts.append(stats_line)

        tweet_parts.append("")

        # Calculate remaining space for why_now
        base = "\n".join(tweet_parts)
        hashtags = "\n#options #trading"
        remaining = 280 - len(base) - len(hashtags) - 1

        if len(why_now) > remaining:
            why_now = why_now[:remaining - 3] + "..."

        tweet_parts.append(why_now)
        tweet_parts.append("#options #trading")

        composed = "\n".join(tweet_parts)

        return f"COMPOSED_POST:\n{composed}\n\nCHARACTER_COUNT: {len(composed)}"

    def _format_threads(
        self, header: str, symbol: str, strategy: str,
        strike: str, expiration: str, premium: str, pop: str, why_now: str
    ) -> str:
        """Format for Threads (500 char limit, more room for detail)."""
        post_parts = [
            f"{header}",
            "",
            f"${symbol} {strategy}",
            ""
        ]

        if strike:
            post_parts.append(f"Strike: {strike}")
        if expiration:
            post_parts.append(f"Expiration: {expiration}")
        if premium:
            post_parts.append(f"Premium: {premium}")
        if pop:
            post_parts.append(f"Probability of Profit: {pop}")

        post_parts.append("")
        post_parts.append(why_now[:300])
        post_parts.append("")
        post_parts.append("#options #trading #stocks")

        composed = "\n".join(post_parts)

        return f"COMPOSED_POST:\n{composed}\n\nCHARACTER_COUNT: {len(composed)}"
