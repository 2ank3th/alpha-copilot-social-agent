"""Tests for CLI entry point (agent/main.py)."""

import pytest
import sys
import json
import os
from unittest.mock import Mock, patch, MagicMock
from io import StringIO


class TestArgumentParsing:
    """Tests for CLI argument parsing."""

    @patch("agent.main.Config")
    @patch("agent.main.create_agent")
    def test_post_morning_argument(self, mock_create_agent, mock_config):
        """Test --post morning argument is accepted."""
        from agent.main import main

        mock_config.DRY_RUN = True
        mock_config.ENABLE_PROMO_POST = True
        mock_config.ALPHA_COPILOT_API_URL = "http://localhost:8002"
        mock_config.LLM_MODEL = "gemini-2.0-flash-exp"
        mock_config.SUPABASE_EMAIL = None
        mock_config.ALPHA_COPILOT_API_KEY = "test_key"
        mock_config.validate_alpha_copilot.return_value = True
        mock_config.validate_llm.return_value = True
        mock_config.validate_twitter.return_value = True
        mock_config.validate_threads.return_value = True
        mock_config.validate_supabase.return_value = False

        mock_agent = Mock()
        mock_agent.run.return_value = "TASK_COMPLETE: Done"
        mock_create_agent.return_value = mock_agent

        with patch.object(sys, 'argv', ['agent.main', '--post', 'morning']):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 0

    @patch("agent.main.Config")
    @patch("agent.main.create_agent")
    def test_post_eod_argument(self, mock_create_agent, mock_config):
        """Test --post eod argument is accepted."""
        from agent.main import main

        mock_config.DRY_RUN = True
        mock_config.ENABLE_PROMO_POST = True
        mock_config.ALPHA_COPILOT_API_URL = "http://localhost:8002"
        mock_config.LLM_MODEL = "gemini-2.0-flash-exp"
        mock_config.SUPABASE_EMAIL = None
        mock_config.ALPHA_COPILOT_API_KEY = "test_key"
        mock_config.validate_alpha_copilot.return_value = True
        mock_config.validate_llm.return_value = True
        mock_config.validate_twitter.return_value = True
        mock_config.validate_threads.return_value = True
        mock_config.validate_supabase.return_value = False

        mock_agent = Mock()
        mock_agent.run.return_value = "TASK_COMPLETE: Done"
        mock_create_agent.return_value = mock_agent

        with patch.object(sys, 'argv', ['agent.main', '--post', 'eod']):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 0

    @patch("agent.main.Config")
    @patch("agent.main.create_agent")
    def test_custom_task_argument(self, mock_create_agent, mock_config):
        """Test --task argument overrides --post."""
        from agent.main import main

        mock_config.DRY_RUN = True
        mock_config.ENABLE_PROMO_POST = True
        mock_config.ALPHA_COPILOT_API_URL = "http://localhost:8002"
        mock_config.LLM_MODEL = "gemini-2.0-flash-exp"
        mock_config.SUPABASE_EMAIL = None
        mock_config.ALPHA_COPILOT_API_KEY = "test_key"
        mock_config.validate_alpha_copilot.return_value = True
        mock_config.validate_llm.return_value = True
        mock_config.validate_twitter.return_value = True
        mock_config.validate_threads.return_value = True
        mock_config.validate_supabase.return_value = False

        mock_agent = Mock()
        mock_agent.run.return_value = "TASK_COMPLETE: Custom task done"
        mock_create_agent.return_value = mock_agent

        with patch.object(sys, 'argv', ['agent.main', '--task', 'Post about NVDA']):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 0
            # Verify task was passed to agent
            mock_agent.run.assert_called_with('Post about NVDA')

    @patch("agent.main.Config")
    def test_missing_required_args_shows_help(self, mock_config, capsys):
        """Test that missing post/task/eval shows help."""
        from agent.main import main

        mock_config.DRY_RUN = True

        with patch.object(sys, 'argv', ['agent.main']):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 1

    @patch("agent.main.Config")
    def test_sector_post_requires_sector_arg(self, mock_config, capsys):
        """Test --post sector requires --sector argument."""
        from agent.main import main

        mock_config.DRY_RUN = True

        with patch.object(sys, 'argv', ['agent.main', '--post', 'sector']):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 1

        captured = capsys.readouterr()
        assert "sector" in captured.out.lower() or "required" in captured.out.lower()

    @patch("agent.main.Config")
    @patch("agent.main.create_agent")
    def test_dry_run_flag_overrides_config(self, mock_create_agent, mock_config):
        """Test --dry-run flag sets Config.DRY_RUN to True."""
        from agent.main import main

        mock_config.DRY_RUN = False  # Initially false
        mock_config.ENABLE_PROMO_POST = True
        mock_config.ALPHA_COPILOT_API_URL = "http://localhost:8002"
        mock_config.LLM_MODEL = "gemini-2.0-flash-exp"
        mock_config.SUPABASE_EMAIL = None
        mock_config.ALPHA_COPILOT_API_KEY = "test_key"
        mock_config.validate_alpha_copilot.return_value = True
        mock_config.validate_llm.return_value = True
        mock_config.validate_twitter.return_value = True
        mock_config.validate_threads.return_value = True
        mock_config.validate_supabase.return_value = False

        mock_agent = Mock()
        mock_agent.run.return_value = "TASK_COMPLETE: Done"
        mock_create_agent.return_value = mock_agent

        with patch.object(sys, 'argv', ['agent.main', '--post', 'morning', '--dry-run']):
            with pytest.raises(SystemExit):
                main()

        # Verify DRY_RUN was set
        assert mock_config.DRY_RUN == True

    @patch("agent.main.Config")
    @patch("agent.main.create_agent")
    def test_no_promo_flag_disables_promo(self, mock_create_agent, mock_config):
        """Test --no-promo flag disables promotional posts."""
        from agent.main import main

        mock_config.DRY_RUN = True
        mock_config.ENABLE_PROMO_POST = True  # Initially true
        mock_config.ALPHA_COPILOT_API_URL = "http://localhost:8002"
        mock_config.LLM_MODEL = "gemini-2.0-flash-exp"
        mock_config.SUPABASE_EMAIL = None
        mock_config.ALPHA_COPILOT_API_KEY = "test_key"
        mock_config.validate_alpha_copilot.return_value = True
        mock_config.validate_llm.return_value = True
        mock_config.validate_twitter.return_value = True
        mock_config.validate_threads.return_value = True
        mock_config.validate_supabase.return_value = False

        mock_agent = Mock()
        mock_agent.run.return_value = "TASK_COMPLETE: Done"
        mock_create_agent.return_value = mock_agent

        with patch.object(sys, 'argv', ['agent.main', '--post', 'morning', '--no-promo']):
            with pytest.raises(SystemExit):
                main()

        # Verify ENABLE_PROMO_POST was disabled
        assert mock_config.ENABLE_PROMO_POST == False


class TestConfigValidation:
    """Tests for configuration validation in main."""

    @patch("agent.main.Config")
    def test_exits_without_alpha_copilot_config(self, mock_config, capsys):
        """Test exits with error when Alpha Copilot not configured."""
        from agent.main import main

        mock_config.DRY_RUN = True
        mock_config.ENABLE_PROMO_POST = True
        mock_config.ALPHA_COPILOT_API_URL = "http://localhost:8002"
        mock_config.LLM_MODEL = "gemini-2.0-flash-exp"
        mock_config.validate_alpha_copilot.return_value = False
        mock_config.validate_llm.return_value = True
        mock_config.validate_twitter.return_value = True
        mock_config.validate_threads.return_value = True
        mock_config.validate_supabase.return_value = False

        with patch.object(sys, 'argv', ['agent.main', '--post', 'morning']):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 1

        captured = capsys.readouterr()
        assert "ALPHA_COPILOT" in captured.out

    @patch("agent.main.Config")
    def test_exits_without_gemini_config(self, mock_config, capsys):
        """Test exits with error when Gemini not configured."""
        from agent.main import main

        mock_config.DRY_RUN = True
        mock_config.ENABLE_PROMO_POST = True
        mock_config.ALPHA_COPILOT_API_URL = "http://localhost:8002"
        mock_config.LLM_MODEL = "gemini-2.0-flash-exp"
        mock_config.validate_alpha_copilot.return_value = True
        mock_config.validate_llm.return_value = False
        mock_config.validate_twitter.return_value = True
        mock_config.validate_threads.return_value = True
        mock_config.validate_supabase.return_value = False

        with patch.object(sys, 'argv', ['agent.main', '--post', 'morning']):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 1

        captured = capsys.readouterr()
        assert "GEMINI_API_KEY" in captured.out

    @patch("agent.main.Config")
    @patch("agent.main.create_agent")
    def test_warns_without_twitter_in_live_mode(self, mock_create_agent, mock_config, capsys):
        """Test warns when Twitter not configured in non-dry-run mode."""
        from agent.main import main

        mock_config.DRY_RUN = False  # Live mode
        mock_config.ENABLE_PROMO_POST = True
        mock_config.ALPHA_COPILOT_API_URL = "http://localhost:8002"
        mock_config.LLM_MODEL = "gemini-2.0-flash-exp"
        mock_config.SUPABASE_EMAIL = None
        mock_config.ALPHA_COPILOT_API_KEY = "test_key"
        mock_config.validate_alpha_copilot.return_value = True
        mock_config.validate_llm.return_value = True
        mock_config.validate_twitter.return_value = False  # Not configured
        mock_config.validate_threads.return_value = True
        mock_config.validate_supabase.return_value = False

        mock_agent = Mock()
        mock_agent.run.return_value = "TASK_COMPLETE: Done"
        mock_create_agent.return_value = mock_agent

        with patch.object(sys, 'argv', ['agent.main', '--post', 'morning']):
            with pytest.raises(SystemExit):
                main()

        captured = capsys.readouterr()
        assert "Twitter" in captured.out and "WARNING" in captured.out


class TestEvalMode:
    """Tests for evaluation mode."""

    @patch("agent.main.Config")
    @patch("agent.main.create_agent")
    @patch("agent.main.PostEvaluator")
    def test_eval_mode_runs_multiple_iterations(self, mock_evaluator_class, mock_create_agent, mock_config, tmp_path):
        """Test eval mode runs agent multiple times."""
        from agent.main import run_eval_mode
        import argparse

        mock_config.DRY_RUN = True
        mock_config.override.return_value.__enter__ = Mock()
        mock_config.override.return_value.__exit__ = Mock()

        # Mock agent
        mock_agent = Mock()
        mock_agent.run.return_value = "TASK_COMPLETE: Done"
        mock_agent._pending_post = "Test post content #NFA"
        mock_create_agent.return_value = mock_agent

        # Mock evaluator
        mock_evaluator = Mock()
        mock_eval_result = Mock()
        mock_eval_result.hookiness = Mock(total=15)
        mock_eval_result.quality = Mock(total=35)
        mock_eval_result.total = 50
        mock_eval_result.passed = True
        mock_eval_result.failure_reason = ""
        mock_evaluator.evaluate.return_value = mock_eval_result
        mock_evaluator_class.return_value = mock_evaluator

        args = argparse.Namespace(
            runs=3,
            task=None,
            post="morning",
            platform="twitter"
        )

        # Change to temp directory for JSON output
        original_dir = os.getcwd()
        os.chdir(tmp_path)
        try:
            run_eval_mode(args)
        finally:
            os.chdir(original_dir)

        # Verify agent was run 3 times
        assert mock_agent.run.call_count == 3

    @patch("agent.main.Config")
    @patch("agent.main.create_agent")
    @patch("agent.main.PostEvaluator")
    def test_eval_mode_handles_exception(self, mock_evaluator_class, mock_create_agent, mock_config, tmp_path):
        """Test eval mode handles agent exceptions gracefully."""
        from agent.main import run_eval_mode
        import argparse

        mock_config.DRY_RUN = True
        mock_config.override.return_value.__enter__ = Mock()
        mock_config.override.return_value.__exit__ = Mock()

        # Mock agent that raises exception
        mock_agent = Mock()
        mock_agent.run.side_effect = Exception("Agent error")
        mock_create_agent.return_value = mock_agent

        args = argparse.Namespace(
            runs=2,
            task="Test task",
            post=None,
            platform="twitter"
        )

        original_dir = os.getcwd()
        os.chdir(tmp_path)
        try:
            run_eval_mode(args)  # Should not raise
        finally:
            os.chdir(original_dir)

    @patch("agent.main.Config")
    @patch("agent.main.create_agent")
    @patch("agent.main.PostEvaluator")
    def test_eval_mode_saves_json_results(self, mock_evaluator_class, mock_create_agent, mock_config, tmp_path):
        """Test eval mode saves results to JSON file."""
        from agent.main import run_eval_mode
        import argparse

        mock_config.DRY_RUN = True
        mock_config.override.return_value.__enter__ = Mock()
        mock_config.override.return_value.__exit__ = Mock()

        mock_agent = Mock()
        mock_agent.run.return_value = "TASK_COMPLETE: Done"
        mock_agent._pending_post = "Test post #NFA"
        mock_create_agent.return_value = mock_agent

        mock_evaluator = Mock()
        mock_eval_result = Mock()
        mock_eval_result.hookiness = Mock(total=15)
        mock_eval_result.quality = Mock(total=35)
        mock_eval_result.total = 50
        mock_eval_result.passed = True
        mock_eval_result.failure_reason = ""
        mock_evaluator.evaluate.return_value = mock_eval_result
        mock_evaluator_class.return_value = mock_evaluator

        args = argparse.Namespace(
            runs=1,
            task="Test",
            post=None,
            platform="twitter"
        )

        original_dir = os.getcwd()
        os.chdir(tmp_path)
        try:
            run_eval_mode(args)

            # Check JSON file was created
            json_files = list(tmp_path.glob("eval_results_*.json"))
            assert len(json_files) == 1

            # Verify JSON content
            with open(json_files[0]) as f:
                data = json.load(f)
                assert "results" in data
                assert "summary" in data
        finally:
            os.chdir(original_dir)


class TestAgentExecution:
    """Tests for agent execution flow."""

    @patch("agent.main.Config")
    @patch("agent.main.create_agent")
    def test_success_result_exits_zero(self, mock_create_agent, mock_config):
        """Test successful agent result exits with code 0."""
        from agent.main import main

        mock_config.DRY_RUN = True
        mock_config.ENABLE_PROMO_POST = True
        mock_config.ALPHA_COPILOT_API_URL = "http://localhost:8002"
        mock_config.LLM_MODEL = "gemini-2.0-flash-exp"
        mock_config.SUPABASE_EMAIL = None
        mock_config.ALPHA_COPILOT_API_KEY = "test_key"
        mock_config.validate_alpha_copilot.return_value = True
        mock_config.validate_llm.return_value = True
        mock_config.validate_twitter.return_value = True
        mock_config.validate_threads.return_value = True
        mock_config.validate_supabase.return_value = False

        mock_agent = Mock()
        mock_agent.run.return_value = "SUCCESS: Posted to twitter"
        mock_create_agent.return_value = mock_agent

        with patch.object(sys, 'argv', ['agent.main', '--post', 'morning']):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 0

    @patch("agent.main.Config")
    @patch("agent.main.create_agent")
    def test_non_success_result_exits_one(self, mock_create_agent, mock_config):
        """Test non-success agent result exits with code 1."""
        from agent.main import main

        mock_config.DRY_RUN = True
        mock_config.ENABLE_PROMO_POST = True
        mock_config.ALPHA_COPILOT_API_URL = "http://localhost:8002"
        mock_config.LLM_MODEL = "gemini-2.0-flash-exp"
        mock_config.SUPABASE_EMAIL = None
        mock_config.ALPHA_COPILOT_API_KEY = "test_key"
        mock_config.validate_alpha_copilot.return_value = True
        mock_config.validate_llm.return_value = True
        mock_config.validate_twitter.return_value = True
        mock_config.validate_threads.return_value = True
        mock_config.validate_supabase.return_value = False

        mock_agent = Mock()
        mock_agent.run.return_value = "FAILED: Could not complete"
        mock_create_agent.return_value = mock_agent

        with patch.object(sys, 'argv', ['agent.main', '--post', 'morning']):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 1

    @patch("agent.main.Config")
    @patch("agent.main.create_agent")
    def test_agent_exception_exits_one(self, mock_create_agent, mock_config, capsys):
        """Test agent exception exits with code 1."""
        from agent.main import main

        mock_config.DRY_RUN = True
        mock_config.ENABLE_PROMO_POST = True
        mock_config.ALPHA_COPILOT_API_URL = "http://localhost:8002"
        mock_config.LLM_MODEL = "gemini-2.0-flash-exp"
        mock_config.SUPABASE_EMAIL = None
        mock_config.ALPHA_COPILOT_API_KEY = "test_key"
        mock_config.validate_alpha_copilot.return_value = True
        mock_config.validate_llm.return_value = True
        mock_config.validate_twitter.return_value = True
        mock_config.validate_threads.return_value = True
        mock_config.validate_supabase.return_value = False

        mock_create_agent.return_value.run.side_effect = Exception("Agent crashed")

        with patch.object(sys, 'argv', ['agent.main', '--post', 'morning']):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 1

        captured = capsys.readouterr()
        assert "ERROR" in captured.out
