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
        "Get the BIGGEST stock market news right now using Google Search. "
        "Returns the top moving stock or most important news of the day. "
        "USE THIS FIRST to find a timely opportunity to post about."
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
                "properties": {},
                "required": []
            }
        }

    def execute(self) -> str:
        """Fetch the biggest market news using Gemini with grounding."""
        logger.info("Fetching biggest market news via Google Search grounding")

        if not Config.GEMINI_API_KEY:
            return "ERROR: GEMINI_API_KEY not configured."

        query = (
            "What is the single biggest US stock market news story RIGHT NOW? "
            "Focus on ONE stock that is moving significantly today or has major news. "
            "Include:\n"
            "1. The ticker symbol\n"
            "2. What happened (earnings, FDA approval, upgrade, price movement, etc.)\n"
            "3. The percentage move if applicable\n"
            "Be specific with the ticker and numbers. Just give me the ONE most important story."
        )

        try:
            response = self.model.generate_content(query)

            if not response.text:
                return "ERROR: No response from Gemini."

            # Format the response
            result = self._format_response(response.text)
            return result

        except Exception as e:
            logger.exception("Failed to fetch market news")
            return f"ERROR: Failed to fetch market news: {str(e)}"

    def _format_response(self, text: str) -> str:
        """Format the grounded response for the agent."""
        lines = [
            "TODAY'S BIGGEST NEWS (via Google Search):",
            "=" * 40,
            "",
            text.strip(),
            "",
            "=" * 40,
            "",
            "NEXT STEP: Query Alpha Copilot for an options play on this stock.",
            "Remember to check recent posts first to avoid duplicates!",
        ]
        return "\n".join(lines)
