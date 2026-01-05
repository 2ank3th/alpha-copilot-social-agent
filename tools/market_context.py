"""Tool for fetching real-time market context to make posts more relevant."""

import logging
from datetime import datetime
from typing import Dict, Any, List

import httpx

from .base import BaseTool
from agent.config import Config

logger = logging.getLogger(__name__)


class GetMarketContextTool(BaseTool):
    """Fetch current market context for timely, relevant posts."""

    name = "get_market_context"
    description = (
        "Get current market context including top movers, earnings calendar, "
        "and market sentiment. Use this BEFORE querying Alpha Copilot to make "
        "posts timely and relevant to what's happening TODAY."
    )

    def __init__(self):
        self.api_url = Config.ALPHA_COPILOT_API_URL
        self.api_key = Config.ALPHA_COPILOT_API_KEY
        self.timeout = 30.0

    def get_schema(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "context_type": {
                        "type": "string",
                        "enum": ["movers", "earnings", "volatility", "all"],
                        "description": "Type of market context to fetch"
                    }
                },
                "required": ["context_type"]
            }
        }

    def execute(self, context_type: str = "all") -> str:
        """Fetch market context from Alpha Copilot backend."""
        logger.info(f"Fetching market context: {context_type}")

        if not self.api_key:
            return "ERROR: ALPHA_COPILOT_API_KEY not configured."

        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }

            with httpx.Client(timeout=self.timeout) as client:
                response = client.get(
                    f"{self.api_url}/api/market-context",
                    headers=headers,
                    params={"type": context_type}
                )
                response.raise_for_status()
                data = response.json()

            return self._format_context(data, context_type)

        except httpx.HTTPError as e:
            logger.warning(f"Failed to fetch market context: {e}")
            # Return fallback context so agent can still proceed
            return self._get_fallback_context()
        except Exception as e:
            logger.exception("Error fetching market context")
            return self._get_fallback_context()

    def _format_context(self, data: Dict, context_type: str) -> str:
        """Format market context for the agent."""
        parts = [f"MARKET_CONTEXT ({datetime.now().strftime('%Y-%m-%d %H:%M')}):", ""]

        # Top movers
        if movers := data.get("movers", []):
            parts.append("TOP MOVERS TODAY:")
            for m in movers[:5]:
                symbol = m.get("symbol", "?")
                change = m.get("change_percent", 0)
                direction = "🟢" if change > 0 else "🔴"
                reason = m.get("reason", "")
                parts.append(f"  {direction} {symbol}: {change:+.1f}% - {reason}")
            parts.append("")

        # Earnings
        if earnings := data.get("earnings", []):
            parts.append("EARNINGS THIS WEEK:")
            for e in earnings[:5]:
                symbol = e.get("symbol", "?")
                date = e.get("date", "?")
                timing = e.get("timing", "")  # BMO/AMC
                parts.append(f"  📅 {symbol} - {date} ({timing})")
            parts.append("")

        # High IV stocks
        if high_iv := data.get("high_iv", []):
            parts.append("ELEVATED IV (premium selling opportunities):")
            for stock in high_iv[:5]:
                symbol = stock.get("symbol", "?")
                iv_rank = stock.get("iv_rank", 0)
                iv_percentile = stock.get("iv_percentile", 0)
                parts.append(f"  🔥 {symbol}: IV Rank {iv_rank}% | IV Percentile {iv_percentile}%")
            parts.append("")

        # Market sentiment
        if sentiment := data.get("sentiment", {}):
            vix = sentiment.get("vix", 0)
            spy_change = sentiment.get("spy_change", 0)
            market_mood = "BULLISH" if spy_change > 0.5 else "BEARISH" if spy_change < -0.5 else "NEUTRAL"
            parts.append(f"MARKET SENTIMENT: {market_mood}")
            parts.append(f"  VIX: {vix:.1f} | SPY: {spy_change:+.1f}%")
            parts.append("")

        # Trading suggestion
        parts.append("SUGGESTED FOCUS:")
        if movers:
            top_mover = movers[0]
            parts.append(f"  - {top_mover.get('symbol')} is moving {top_mover.get('change_percent', 0):+.1f}% - timely opportunity")
        if earnings:
            next_earnings = earnings[0]
            parts.append(f"  - {next_earnings.get('symbol')} earnings {next_earnings.get('date')} - play the IV crush")
        if high_iv:
            high_iv_stock = high_iv[0]
            parts.append(f"  - {high_iv_stock.get('symbol')} IV rank {high_iv_stock.get('iv_rank')}% - premium selling setup")

        return "\n".join(parts)

    def _get_fallback_context(self) -> str:
        """Return fallback context when API fails."""
        return """MARKET_CONTEXT (fallback - API unavailable):

Use these attention-grabbing approaches:
- Focus on stocks with upcoming earnings (check financial calendars)
- Look for stocks making 52-week highs/lows
- Find elevated IV situations for premium selling
- Reference current market conditions (VIX level, trend)

SUGGESTED QUERIES:
- "Find high IV stocks for premium selling"
- "Find earnings plays for this week"
- "Find momentum stocks breaking out"
"""
