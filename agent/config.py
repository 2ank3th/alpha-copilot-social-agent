"""Configuration for the Alpha Copilot Social Agent."""

import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Agent configuration loaded from environment variables."""

    # Alpha Copilot Backend API
    ALPHA_COPILOT_API_URL: str = os.getenv(
        "ALPHA_COPILOT_API_URL",
        "http://localhost:8002"
    )

    # LLM Configuration
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    LLM_MODEL: str = os.getenv("LLM_MODEL", "gemini-2.0-flash")
    LLM_TIMEOUT: int = int(os.getenv("LLM_TIMEOUT", "60"))

    # Twitter/X Credentials
    TWITTER_API_KEY: str = os.getenv("TWITTER_API_KEY", "")
    TWITTER_API_SECRET: str = os.getenv("TWITTER_API_SECRET", "")
    TWITTER_ACCESS_TOKEN: str = os.getenv("TWITTER_ACCESS_TOKEN", "")
    TWITTER_ACCESS_SECRET: str = os.getenv("TWITTER_ACCESS_SECRET", "")
    TWITTER_BEARER_TOKEN: str = os.getenv("TWITTER_BEARER_TOKEN", "")

    # Agent Settings
    MAX_ITERATIONS: int = int(os.getenv("MAX_ITERATIONS", "10"))
    DRY_RUN: bool = os.getenv("DRY_RUN", "true").lower() == "true"

    @classmethod
    def validate_llm(cls) -> bool:
        """Check if LLM configuration is valid."""
        return bool(cls.GEMINI_API_KEY)

    @classmethod
    def validate_twitter(cls) -> bool:
        """Check if Twitter credentials are configured."""
        return all([
            cls.TWITTER_API_KEY,
            cls.TWITTER_API_SECRET,
            cls.TWITTER_ACCESS_TOKEN,
            cls.TWITTER_ACCESS_SECRET,
        ])

    @classmethod
    def get_enabled_platforms(cls) -> list:
        """Return list of platforms with valid credentials."""
        platforms = []
        if cls.validate_twitter():
            platforms.append("twitter")
        # Add more platforms here as they're implemented
        return platforms
