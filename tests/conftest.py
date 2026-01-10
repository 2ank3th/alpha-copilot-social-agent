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
