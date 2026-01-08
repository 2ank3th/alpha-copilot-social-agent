"""Tool for fetching real-time market news using Gemini with Google Search grounding."""

import logging
import time
from typing import Dict, Any

from google import genai
from google.genai import types
from google.genai.errors import ServerError

from .base import BaseTool
from agent.config import Config

logger = logging.getLogger(__name__)

# Retry configuration
MAX_RETRIES = 3
RETRY_DELAY_SECONDS = 2.0
RETRY_BACKOFF_MULTIPLIER = 2.0


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

        # Retry loop for transient errors
        last_error = None
        delay = RETRY_DELAY_SECONDS

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                # Generate with grounding
                response = self.client.models.generate_content(
                    model=self.model_name,
                    contents=query,
                    config=config,
                )

                if not response.text:
                    return "ERROR: No response from Gemini."

                # Format the response
                result = self._format_response(response.text)
                return result

            except ServerError as e:
                # Retry on 500/503 server errors
                last_error = e
                if attempt < MAX_RETRIES:
                    logger.warning(
                        f"Gemini server error (attempt {attempt}/{MAX_RETRIES}): {e}. "
                        f"Retrying in {delay:.1f}s..."
                    )
                    time.sleep(delay)
                    delay *= RETRY_BACKOFF_MULTIPLIER
                else:
                    logger.error(f"Gemini server error after {MAX_RETRIES} attempts")
                    # Fallback to non-grounded if grounding fails
                    if self.grounding_enabled:
                        logger.warning("Falling back to non-grounded generation")
                        return self._fallback_generation(query)
                    return f"ERROR: Failed to fetch market news after {MAX_RETRIES} retries"

            except Exception as e:
                logger.exception("Failed to fetch market news")
                # Fallback to non-grounded if grounding fails
                if self.grounding_enabled:
                    logger.warning("Grounding failed, falling back to non-grounded generation")
                    return self._fallback_generation(query)
                return f"ERROR: Failed to fetch market news: {str(e)}"

        # Should not reach here
        if last_error:
            return f"ERROR: {str(last_error)}"

    def _fallback_generation(self, query: str) -> str:
        """Fallback to non-grounded generation if grounding fails."""
        try:
            config = types.GenerateContentConfig(temperature=0.7)
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=query,
                config=config,
            )

            if response.text:
                return self._format_response(response.text)

        except Exception as e:
            logger.error(f"Fallback generation also failed: {e}")

        # Final fallback - return helpful message
        return (
            "MARKET NEWS TOOL UNAVAILABLE\n"
            "\n"
            "Please proceed using your general market knowledge:\n"
            "- Focus on well-known, liquid stocks (AAPL, NVDA, TSLA, MSFT, etc.)\n"
            "- Consider stocks with typically high implied volatility\n"
            "- Mention general market conditions or sector trends if relevant\n"
            "\n"
            "Remember to check recent posts first to avoid duplicates!"
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
