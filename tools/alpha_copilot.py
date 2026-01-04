"""Tool for querying the Alpha Copilot backend API."""

import logging
import httpx
import uuid
from typing import Dict, Any

from .base import BaseTool
from agent.config import Config

logger = logging.getLogger(__name__)


class QueryAlphaCopilotTool(BaseTool):
    """Query the Alpha Copilot backend for options analysis."""

    name = "query_alpha_copilot"
    description = "Query the Alpha Copilot API for options trading analysis. Uses the same API as the web app."

    def __init__(self):
        self.api_url = Config.ALPHA_COPILOT_API_URL
        self.api_key = Config.ALPHA_COPILOT_API_KEY
        self.timeout = 120.0  # LLM processing can take time

    def get_schema(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Natural language query for options analysis (e.g., 'Find covered call opportunities for AAPL, MSFT')"
                    }
                },
                "required": ["query"]
            }
        }

    def execute(self, query: str) -> str:
        """Execute query against Alpha Copilot API."""
        logger.info(f"Querying Alpha Copilot: {query}")

        if not self.api_key:
            return "ERROR: ALPHA_COPILOT_API_KEY not configured. Cannot query the API."

        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }

            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(
                    f"{self.api_url}/api/query",
                    headers=headers,
                    json={
                        "query": query,
                        "session_id": f"social_agent_{uuid.uuid4().hex[:8]}"
                    }
                )
                response.raise_for_status()
                data = response.json()

            status = data.get("status", "unknown")

            if status == "needs_clarification":
                message = data.get("message", "Need more information")
                return f"CLARIFICATION_NEEDED: {message}"

            if status != "success":
                error = data.get("error_message", "Unknown error")
                return f"ERROR: {error}"

            # Extract key information from response
            analysis = data.get("analysis", {})
            recommendations = analysis.get("recommendations", [])
            market_overview = analysis.get("market_overview", "")

            if not recommendations:
                return "NO_RECOMMENDATIONS: The query returned no options recommendations."

            # Format recommendations for agent context
            result_parts = []
            result_parts.append(f"QUERY: {query}")
            result_parts.append(f"STATUS: success")
            result_parts.append(f"MARKET_OVERVIEW: {market_overview}")
            result_parts.append(f"RECOMMENDATIONS_COUNT: {len(recommendations)}")
            result_parts.append("")

            for i, rec in enumerate(recommendations[:3], 1):  # Top 3
                symbol = rec.get("symbol", "?")
                strategy = rec.get("strategy", "?")
                rationale = rec.get("rationale", "")

                # Extract key metrics
                metrics = []
                if rec.get("strike"):
                    metrics.append(f"Strike: ${rec['strike']}")
                if rec.get("premium"):
                    metrics.append(f"Premium: ${rec['premium']}")
                if rec.get("probability_of_profit"):
                    metrics.append(f"POP: {rec['probability_of_profit']}%")
                if rec.get("expiration"):
                    metrics.append(f"Exp: {rec['expiration']}")
                if rec.get("delta"):
                    metrics.append(f"Delta: {rec['delta']}")

                result_parts.append(f"RECOMMENDATION {i}:")
                result_parts.append(f"  Symbol: {symbol}")
                result_parts.append(f"  Strategy: {strategy}")
                result_parts.append(f"  Metrics: {', '.join(metrics)}")
                result_parts.append(f"  Rationale: {rationale[:200]}...")
                result_parts.append("")

            return "\n".join(result_parts)

        except httpx.TimeoutException:
            return "ERROR: Request timed out. The Alpha Copilot API is taking too long."
        except httpx.HTTPError as e:
            return f"ERROR: HTTP error: {e}"
        except Exception as e:
            logger.exception("Failed to query Alpha Copilot")
            return f"ERROR: {str(e)}"
