"""End-to-end tests for the agent flow.

These tests require real API keys and run the full agent loop.
They are marked with @pytest.mark.e2e and skipped by default.

Run with: pytest -m e2e
"""

import os
import pytest

from agent.config import Config
from agent.loop import create_agent
from prompts.system import get_task_prompt


def _get_missing_credentials() -> list[str]:
    """Check which required credentials are missing."""
    missing = []

    # LLM is always required
    if not os.getenv("GEMINI_API_KEY"):
        missing.append("GEMINI_API_KEY")

    # Alpha Copilot needs either API key or Supabase auth
    has_api_key = bool(os.getenv("ALPHA_COPILOT_API_KEY"))
    has_supabase = all([
        os.getenv("SUPABASE_URL"),
        os.getenv("SUPABASE_ANON_KEY"),
        os.getenv("SUPABASE_EMAIL"),
        os.getenv("SUPABASE_PASSWORD"),
    ])

    if not has_api_key and not has_supabase:
        missing.append("ALPHA_COPILOT_API_KEY or SUPABASE credentials")

    return missing


@pytest.mark.e2e
class TestE2EAgentFlow:
    """End-to-end tests for the complete agent flow."""

    def test_agent_completes_and_passes_evaluation(self):
        """
        Test that the agent can complete a full run and generate a passing post.

        This test:
        1. Validates required credentials are present (fails if missing)
        2. Runs the agent with a morning post task in dry-run mode
        3. Asserts the agent completes successfully
        4. Asserts the generated post passes quality evaluation
        """
        # 1. Fail if credentials are missing
        missing = _get_missing_credentials()
        if missing:
            pytest.fail(
                f"Missing required credentials: {', '.join(missing)}. "
                "Set these as environment variables or GitHub secrets."
            )

        # 2. Force dry-run mode (safety)
        with Config.override(DRY_RUN=True):
            # 3. Create agent and run task
            agent = create_agent()
            task = get_task_prompt("morning", "twitter")

            result = agent.run(task)

        # 4. Assert agent completed successfully
        assert result is not None, "Agent returned None"

        # Check for failure indicators
        assert "EVAL_FAILED" not in result, f"Post failed evaluation: {result}"
        assert "MAX_ITERATIONS_REACHED" not in result, "Agent hit max iterations without completing"
        assert "ERROR" not in result or "TOOL_ERROR" in result, f"Agent encountered error: {result}"

        # Check for success indicators
        success_indicators = ["TASK_COMPLETE", "SUCCESS", "done"]
        has_success = any(indicator in result for indicator in success_indicators)
        assert has_success, f"Agent did not complete successfully. Result: {result}"

        # 5. Verify a post was generated
        assert agent._pending_post is not None, "No post was generated"
        assert len(agent._pending_post) > 0, "Generated post is empty"

        # 6. Log the generated post for debugging
        print(f"\n{'='*60}")
        print("Generated Post:")
        print(f"{'='*60}")
        print(agent._pending_post)
        print(f"{'='*60}\n")


@pytest.mark.e2e
class TestE2ECredentialValidation:
    """Tests for credential validation."""

    def test_credentials_are_configured(self):
        """Verify all required credentials are present."""
        missing = _get_missing_credentials()
        if missing:
            pytest.fail(
                f"Missing required credentials: {', '.join(missing)}. "
                "Configure these in your environment or GitHub secrets."
            )

        # Additional validation
        assert Config.validate_llm(), "LLM configuration is invalid"
        assert Config.validate_alpha_copilot(), "Alpha Copilot configuration is invalid"
