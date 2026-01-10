"""Tool for fetching real-time market news using Gemini with Google Search grounding."""

import logging
from typing import Dict, Any

from google import genai
from google.genai import types
from google.genai.errors import ServerError

from .base import BaseTool
from agent.config import Config
from agent.retry import retry_with_backoff

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
        self.client = genai.Client(api_key=Config.GEMINI_API_KEY)
        self.model_name = Config.LLM_MODEL
        self.grounding_enabled = Config.ENABLE_GROUNDING

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

        # Build grounding tool if enabled
        tools = []
        if self.grounding_enabled:
            grounding_tool = types.Tool(
                google_search=types.GoogleSearch()
            )
            tools.append(grounding_tool)
            logger.info("Google Search grounding enabled")

        # Configure generation
        config = types.GenerateContentConfig(
            temperature=0.7,
        )
        if tools:
            config.tools = tools

        def _do_fetch():
            """Inner function for retry wrapper."""
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=query,
                config=config,
            )

            if not response.text:
                raise ValueError("No response from Gemini")

            return self._format_response(response.text)

        # Use retry utility for transient server errors
        return retry_with_backoff(
            func=_do_fetch,
            retryable_exceptions=ServerError,
            operation_name="Market news fetch",
        )

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
