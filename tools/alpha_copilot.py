"""Tool for querying the Alpha Copilot backend API."""

import logging
import httpx
import uuid
from typing import Dict, Any, Optional

from .base import BaseTool
from agent.config import Config
from agent.supabase_auth import SupabaseAuth

logger = logging.getLogger(__name__)


class QueryAlphaCopilotTool(BaseTool):
    """Query the Alpha Copilot backend for options analysis."""

    name = "query_alpha_copilot"
    description = "Query the Alpha Copilot API for options trading analysis. Uses the same API as the web app."

    def __init__(self):
        self.api_url = Config.ALPHA_COPILOT_API_URL
        self.api_key = Config.ALPHA_COPILOT_API_KEY
        self.timeout = 120.0  # LLM processing can take time

        # Create reusable HTTP client
        self._client = httpx.Client(timeout=self.timeout)

        # Use Supabase auth if configured, otherwise fall back to static API key
        self._supabase_auth: Optional[SupabaseAuth] = None
        if Config.validate_supabase():
            self._supabase_auth = SupabaseAuth()
            logger.info("Using Supabase authentication for backend API")
        elif self.api_key:
            logger.info("Using static API key for backend API")

    def __del__(self):
        """Clean up HTTP client."""
        if hasattr(self, '_client'):
            self._client.close()

    def _get_auth_token(self) -> Optional[str]:
        """Get authentication token (from Supabase or static API key)."""
        if self._supabase_auth:
            return self._supabase_auth.get_access_token()
        return self.api_key if self.api_key else None

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

        # Get auth token (from Supabase or static API key)
        token = self._get_auth_token()
        if not token:
            if self._supabase_auth:
                return "ERROR: Failed to authenticate with Supabase. Check credentials."
            else:
                return "ERROR: No authentication configured. Set SUPABASE_* or ALPHA_COPILOT_API_KEY."

        try:
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            }

            response = self._client.post(
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
        except httpx.HTTPStatusError as e:
            status = e.response.status_code
            if status == 401:
                # Token might be expired, try to refresh
                if self._supabase_auth:
                    logger.warning("Got 401, attempting token refresh...")
                    success, msg = self._supabase_auth.refresh()
                    if success:
                        # Retry with new token
                        return self.execute(query)
                    else:
                        return f"ERROR: Authentication failed (401). Token refresh failed: {msg}"
                return "ERROR: Authentication failed (401). Check your API key or Supabase credentials."
            elif status == 403:
                return "ERROR: Access forbidden (403). Your account may not have API access."
            else:
                body = e.response.text[:200] if e.response.text else "No details"
                return f"ERROR: HTTP {status}: {body}"
        except httpx.HTTPError as e:
            return f"ERROR: HTTP error: {e}"
        except Exception as e:
            logger.exception("Failed to query Alpha Copilot")
            return f"ERROR: {str(e)}"
