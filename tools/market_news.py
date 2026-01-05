"""Tool for fetching real-time market news using Gemini with Google Search grounding."""

import logging
from typing import Dict, Any

import google.generativeai as genai

from .base import BaseTool
from agent.config import Config

logger = logging.getLogger(__name__)


class GetMarketNewsTool(BaseTool):
    """Fetch real-time market news using Gemini with Google Search grounding."""

    name = "get_market_news"
    description = (
        "Get real-time market news using Google Search. "
        "Returns what's moving in the market TODAY - stock movers, earnings, "
        "breaking news. USE THIS FIRST to find timely opportunities."
    )

    def __init__(self):
        genai.configure(api_key=Config.GEMINI_API_KEY)
        self.model = genai.GenerativeModel(
            model_name=Config.LLM_MODEL,
            tools="google_search_retrieval",  # Enable grounding
        )

    def get_schema(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "focus": {
                        "type": "string",
                        "enum": ["movers", "earnings", "news", "all"],
                        "description": "What to focus on: movers (price action), earnings (upcoming reports), news (breaking stories), or all"
                    }
                },
                "required": ["focus"]
            }
        }

    def execute(self, focus: str = "all") -> str:
        """Fetch market news using Gemini with grounding."""
        logger.info(f"Fetching market news with focus: {focus}")

        if not Config.GEMINI_API_KEY:
            return "ERROR: GEMINI_API_KEY not configured."

        # Build query based on focus
        queries = {
            "movers": (
                "What are the top 5 stocks moving today in the US stock market? "
                "Include the ticker symbol, percentage change, and reason for the move. "
                "Focus on stocks with significant moves (3%+ up or down)."
            ),
            "earnings": (
                "What major US companies have earnings reports coming up this week? "
                "Include the ticker symbol, earnings date, and whether it's before or after market. "
                "Focus on popular stocks that options traders would care about."
            ),
            "news": (
                "What are the top 3 breaking stock market news stories today? "
                "Focus on news that would affect specific stocks - FDA approvals, "
                "analyst upgrades/downgrades, M&A, guidance changes."
            ),
            "all": (
                "Give me a quick market update for options traders:\n"
                "1. Top 3 stocks moving big today (ticker, % change, why)\n"
                "2. Any earnings this week for major stocks\n"
                "3. Any breaking news affecting specific stocks\n"
                "Be specific with ticker symbols and numbers."
            ),
        }

        query = queries.get(focus, queries["all"])

        try:
            response = self.model.generate_content(query)

            if not response.text:
                return "ERROR: No response from Gemini."

            # Format the response
            result = self._format_response(response.text, focus)
            return result

        except Exception as e:
            logger.exception("Failed to fetch market news")
            return f"ERROR: Failed to fetch market news: {str(e)}"

    def _format_response(self, text: str, focus: str) -> str:
        """Format the grounded response for the agent."""
        lines = [
            "MARKET NEWS (Live from Google Search):",
            "=" * 40,
            "",
            text.strip(),
            "",
            "=" * 40,
            "",
            "NEXT STEPS:",
            "- Pick a stock from above that has a clear catalyst",
            "- Query Alpha Copilot for options strategies on that stock",
            "- Reference the news/catalyst in your post for engagement",
        ]
        return "\n".join(lines)
