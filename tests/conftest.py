"""Pytest configuration and shared fixtures."""

import pytest
import os

# Ensure we're in test mode
os.environ.setdefault("DRY_RUN", "true")


@pytest.fixture
def sample_good_post():
    """A sample post that should pass evaluation."""
    return """$NVDA (Nvidia) just hit all-time highs on AI chip demand surge!

Here's how to profit:
→ Sell the $950 call (Jan 17)
→ Collect ~$12 premium
→ ~75% POP

#NVDA #options #NFA"""


@pytest.fixture
def sample_bad_post():
    """A sample post that should fail evaluation."""
    return "AAPL | $180 | $3.50 | 72%"


@pytest.fixture
def sample_twitter_length_post():
    """A post exactly at Twitter's limit."""
    base = "$NVDA up 5%! Sell $950 call, Jan 17, $12 premium, 75% POP. "
    padding = "x" * (280 - len(base) - 5)
    return base + padding + " #NFA"


@pytest.fixture
def sample_alpha_copilot_response():
    """Sample API response from Alpha Copilot with recommendations."""
    return {
        "status": "success",
        "analysis": {
            "market_overview": "Bullish sentiment on tech stocks with NVDA leading gains",
            "recommendations": [
                {
                    "symbol": "NVDA",
                    "strategy": "Covered Call",
                    "strike": 950,
                    "premium": 12.50,
                    "probability_of_profit": 75,
                    "expiration": "Jan 17",
                    "delta": 0.30,
                    "rationale": "Strong momentum with high IV makes this an attractive premium selling opportunity"
                },
                {
                    "symbol": "AAPL",
                    "strategy": "Cash Secured Put",
                    "strike": 180,
                    "premium": 3.20,
                    "probability_of_profit": 72,
                    "expiration": "Jan 24",
                    "delta": -0.25,
                    "rationale": "Solid support at $175 makes this a lower-risk entry"
                },
                {
                    "symbol": "MSFT",
                    "strategy": "Iron Condor",
                    "strike": 420,
                    "premium": 5.80,
                    "probability_of_profit": 68,
                    "expiration": "Feb 7",
                    "delta": 0.05,
                    "rationale": "Low volatility environment suits neutral strategy"
                }
            ]
        }
    }


@pytest.fixture
def sample_supabase_login_response():
    """Sample successful Supabase login response."""
    return {
        "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.test_access_token",
        "refresh_token": "test_refresh_token_12345",
        "token_type": "bearer",
        "expires_in": 3600,
        "user": {
            "id": "user-uuid-12345",
            "email": "test@example.com"
        }
    }


@pytest.fixture
def mock_gemini_response():
    """Mock Gemini API response for market news."""
    from unittest.mock import Mock

    mock_response = Mock()
    mock_response.text = "$NVDA up 5% today on AI chip demand surge! Nvidia reports strong Q4 guidance."

    # Mock grounding metadata
    mock_chunk = Mock()
    mock_chunk.web = Mock()
    mock_chunk.web.uri = "https://example.com/nvda-news"
    mock_chunk.web.title = "NVDA Stock Surges on AI Demand"

    mock_metadata = Mock()
    mock_metadata.grounding_chunks = [mock_chunk]
    mock_metadata.web_search_queries = ["NVDA stock news today"]

    mock_candidate = Mock()
    mock_candidate.grounding_metadata = mock_metadata

    mock_response.candidates = [mock_candidate]

    return mock_response
