"""Configuration for the Alpha Copilot Social Agent."""

import os
from contextlib import contextmanager
from typing import Any, Dict, Iterator
from dotenv import load_dotenv

# Load .env first, then .env.local overrides
load_dotenv()
load_dotenv(".env.local", override=True)


class Config:
    """Agent configuration loaded from environment variables."""

    # Alpha Copilot Backend API
    ALPHA_COPILOT_API_URL: str = os.getenv(
        "ALPHA_COPILOT_API_URL",
        "http://localhost:8002"
    )
    ALPHA_COPILOT_API_KEY: str = os.getenv("ALPHA_COPILOT_API_KEY", "")

    # Supabase Authentication (same flow as frontend)
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
    SUPABASE_ANON_KEY: str = os.getenv("SUPABASE_ANON_KEY", "")
    SUPABASE_EMAIL: str = os.getenv("SUPABASE_EMAIL", "")
    SUPABASE_PASSWORD: str = os.getenv("SUPABASE_PASSWORD", "")

    # LLM Configuration
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    LLM_MODEL: str = os.getenv("LLM_MODEL", "gemini-3-flash-preview")
    LLM_TIMEOUT: int = int(os.getenv("LLM_TIMEOUT", "60"))
    ENABLE_GROUNDING: bool = os.getenv("ENABLE_GROUNDING", "true").lower() == "true"

    # Twitter/X Credentials
    TWITTER_API_KEY: str = os.getenv("TWITTER_API_KEY", "")
    TWITTER_API_SECRET: str = os.getenv("TWITTER_API_SECRET", "")
    TWITTER_ACCESS_TOKEN: str = os.getenv("TWITTER_ACCESS_TOKEN", "")
    TWITTER_ACCESS_SECRET: str = os.getenv("TWITTER_ACCESS_SECRET", "")
    TWITTER_BEARER_TOKEN: str = os.getenv("TWITTER_BEARER_TOKEN", "")

    # Threads Credentials (Meta Graph API)
    THREADS_ACCESS_TOKEN: str = os.getenv("THREADS_ACCESS_TOKEN", "")
    THREADS_USER_ID: str = os.getenv("THREADS_USER_ID", "")

    # Alpha Copilot Promotional Settings
    ALPHA_COPILOT_URL: str = os.getenv(
        "ALPHA_COPILOT_URL",
        "https://alphacopilot.ai"
    )
    ENABLE_PROMO_POST: bool = os.getenv("ENABLE_PROMO_POST", "true").lower() == "true"

    # Agent Settings
    MAX_ITERATIONS: int = int(os.getenv("MAX_ITERATIONS", "10"))
    DRY_RUN: bool = os.getenv("DRY_RUN", "true").lower() == "true"

    # Evaluation Thresholds
    EVAL_HOOKINESS_MIN: int = int(os.getenv("EVAL_HOOKINESS_MIN", "15"))  # 15/25 = 60%
    EVAL_QUALITY_MIN: int = int(os.getenv("EVAL_QUALITY_MIN", "30"))      # 30/50 = 60%
    EVAL_TOTAL_MIN: int = int(os.getenv("EVAL_TOTAL_MIN", "45"))          # 45/75 = 60%
    EVAL_MODE: str = os.getenv("EVAL_MODE", "both")  # hookiness|quality|both

    @classmethod
    def validate_llm(cls) -> bool:
        """Check if LLM configuration is valid."""
        return bool(cls.GEMINI_API_KEY)

    @classmethod
    def validate_alpha_copilot(cls) -> bool:
        """Check if Alpha Copilot API credentials are configured."""
        # Check for either static API key or Supabase auth
        return bool(cls.ALPHA_COPILOT_API_KEY) or cls.validate_supabase()

    @classmethod
    def validate_supabase(cls) -> bool:
        """Check if Supabase credentials are configured."""
        return all([
            cls.SUPABASE_URL,
            cls.SUPABASE_ANON_KEY,
            cls.SUPABASE_EMAIL,
            cls.SUPABASE_PASSWORD,
        ])

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
    def validate_threads(cls) -> bool:
        """Check if Threads credentials are configured."""
        return all([
            cls.THREADS_ACCESS_TOKEN,
            cls.THREADS_USER_ID,
        ])

    @classmethod
    def get_enabled_platforms(cls) -> list:
        """Return list of platforms with valid credentials."""
        platforms = []
        if cls.validate_twitter():
            platforms.append("twitter")
        if cls.validate_threads():
            platforms.append("threads")
        return platforms

    @classmethod
    @contextmanager
    def override(cls, **kwargs: Any) -> Iterator[None]:
        """Temporarily override config values.

        Usage:
            with Config.override(DRY_RUN=True, ENABLE_PROMO_POST=False):
                # Config values are temporarily changed
                run_agent()
            # Original values are restored
        """
        original: Dict[str, Any] = {}
        for key in kwargs:
            if hasattr(cls, key):
                original[key] = getattr(cls, key)
            else:
                raise ValueError(f"Unknown config key: {key}")

        try:
            for key, value in kwargs.items():
                setattr(cls, key, value)
            yield
        finally:
            for key, value in original.items():
                setattr(cls, key, value)
