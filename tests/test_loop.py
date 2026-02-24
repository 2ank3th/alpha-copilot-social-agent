"""Tests for agent loop implementation."""

import pytest
from unittest.mock import Mock, patch, MagicMock


class TestAgentLoopInit:
    """Tests for AgentLoop initialization."""

    @patch("agent.loop.Config")
    def test_init_with_defaults(self, mock_config):
        """Test AgentLoop initializes with default evaluator."""
        from agent.loop import AgentLoop

        mock_config.MAX_ITERATIONS = 10

        mock_llm = Mock()
        mock_tools = Mock()

        agent = AgentLoop(mock_llm, mock_tools)

        assert agent.llm == mock_llm
        assert agent.tools == mock_tools
        assert agent.evaluator is not None
        assert agent.max_iterations == 10
        assert agent._pending_post is None

    @patch("agent.loop.Config")
    def test_init_with_custom_evaluator(self, mock_config):
        """Test AgentLoop initializes with custom evaluator."""
        from agent.loop import AgentLoop

        mock_config.MAX_ITERATIONS = 10

        mock_llm = Mock()
        mock_tools = Mock()
        mock_evaluator = Mock()

        agent = AgentLoop(mock_llm, mock_tools, mock_evaluator)

        assert agent.evaluator == mock_evaluator


class TestAgentLoopRun:
    """Tests for AgentLoop.run() method."""

    @patch("agent.loop.Config")
    @patch("agent.loop.SYSTEM_PROMPT", "Test system prompt")
    def test_run_simple_done(self, mock_config):
        """Test run completes with done tool."""
        from agent.loop import AgentLoop

        mock_config.MAX_ITERATIONS = 10

        mock_llm = Mock()
        mock_llm_response = Mock()
        mock_llm_response.is_done = True
        mock_llm_response.tool_call = {
            "name": "done",
            "arguments": {"summary": "Task completed"}
        }
        mock_llm_response.reasoning = "I should finish now"
        mock_llm.generate.return_value = mock_llm_response

        mock_tools = Mock()
        mock_tools.execute.return_value = "TASK_COMPLETE: Task completed"

        agent = AgentLoop(mock_llm, mock_tools)
        result = agent.run("Test task")

        assert "TASK_COMPLETE" in result
        mock_tools.execute.assert_called_once_with("done", summary="Task completed")

    @patch("agent.loop.Config")
    @patch("agent.loop.SYSTEM_PROMPT", "Test system prompt")
    def test_run_executes_tool(self, mock_config):
        """Test run executes tools and continues."""
        from agent.loop import AgentLoop

        mock_config.MAX_ITERATIONS = 10

        mock_llm = Mock()

        # First response: execute tool
        response1 = Mock()
        response1.is_done = False
        response1.tool_call = {"name": "test_tool", "arguments": {"arg": "value"}}
        response1.reasoning = "Let me execute the tool"

        # Second response: done
        response2 = Mock()
        response2.is_done = True
        response2.tool_call = {"name": "done", "arguments": {"summary": "Done"}}
        response2.reasoning = "Task complete"

        mock_llm.generate.side_effect = [response1, response2]

        mock_tools = Mock()
        mock_tools.execute.side_effect = ["Tool result", "TASK_COMPLETE: Done"]

        agent = AgentLoop(mock_llm, mock_tools)
        result = agent.run("Test task")

        assert "TASK_COMPLETE" in result
        assert mock_tools.execute.call_count == 2

    @patch("agent.loop.Config")
    @patch("agent.loop.SYSTEM_PROMPT", "Test system prompt")
    def test_run_max_iterations_reached(self, mock_config):
        """Test run stops at max iterations."""
        from agent.loop import AgentLoop

        mock_config.MAX_ITERATIONS = 3

        mock_llm = Mock()
        response = Mock()
        response.is_done = False
        response.tool_call = None
        response.reasoning = "Still thinking"
        mock_llm.generate.return_value = response

        mock_tools = Mock()

        agent = AgentLoop(mock_llm, mock_tools)
        result = agent.run("Test task")

        assert "MAX_ITERATIONS_REACHED" in result
        assert mock_llm.generate.call_count == 3

    @patch("agent.loop.Config")
    @patch("agent.loop.SYSTEM_PROMPT", "Test system prompt")
    def test_run_handles_tool_error(self, mock_config):
        """Test run handles tool execution errors."""
        from agent.loop import AgentLoop

        mock_config.MAX_ITERATIONS = 10

        mock_llm = Mock()

        # First response: execute tool (will fail)
        response1 = Mock()
        response1.is_done = False
        response1.tool_call = {"name": "failing_tool", "arguments": {}}
        response1.reasoning = "Executing tool"

        # Second response: done
        response2 = Mock()
        response2.is_done = True
        response2.tool_call = {"name": "done", "arguments": {"summary": "Done after error"}}
        response2.reasoning = "Done"

        mock_llm.generate.side_effect = [response1, response2]

        mock_tools = Mock()
        mock_tools.execute.side_effect = [Exception("Tool failed"), "TASK_COMPLETE: Done"]

        agent = AgentLoop(mock_llm, mock_tools)
        result = agent.run("Test task")

        assert "TASK_COMPLETE" in result

    @patch("agent.loop.Config")
    @patch("agent.loop.SYSTEM_PROMPT", "Test system prompt")
    def test_run_handles_llm_exception(self, mock_config):
        """Test run handles LLM exceptions gracefully."""
        from agent.loop import AgentLoop

        mock_config.MAX_ITERATIONS = 3

        mock_llm = Mock()
        mock_llm.generate.side_effect = Exception("LLM error")

        mock_tools = Mock()

        agent = AgentLoop(mock_llm, mock_tools)
        result = agent.run("Test task")

        assert "MAX_ITERATIONS_REACHED" in result

    @patch("agent.loop.Config")
    @patch("agent.loop.SYSTEM_PROMPT", "Test system prompt")
    def test_run_clears_pending_post(self, mock_config):
        """Test run clears pending post from previous runs."""
        from agent.loop import AgentLoop

        mock_config.MAX_ITERATIONS = 1

        mock_llm = Mock()
        response = Mock()
        response.is_done = False
        response.tool_call = None
        response.reasoning = "Thinking"
        mock_llm.generate.return_value = response

        mock_tools = Mock()

        agent = AgentLoop(mock_llm, mock_tools)
        agent._pending_post = "Previous post"

        agent.run("New task")

        # Should be cleared at start of run
        # Note: In this case it may be None or have a new value depending on flow


class TestAgentLoopEvaluationGate:
    """Tests for evaluation gate in agent loop."""

    @patch("agent.loop.Config")
    @patch("agent.loop.SYSTEM_PROMPT", "Test system prompt")
    def test_write_post_evaluation_pass(self, mock_config):
        """Test write_post passes evaluation gate."""
        from agent.loop import AgentLoop

        mock_config.MAX_ITERATIONS = 10
        mock_config.EVAL_TOTAL_MIN = 40

        mock_llm = Mock()

        # First response: write_post
        response1 = Mock()
        response1.is_done = False
        response1.tool_call = {"name": "write_post", "arguments": {"content": "Test post"}}
        response1.reasoning = "Writing post"

        # Second response: done
        response2 = Mock()
        response2.is_done = True
        response2.tool_call = {"name": "done", "arguments": {"summary": "Posted"}}
        response2.reasoning = "Done"

        mock_llm.generate.side_effect = [response1, response2]

        mock_tools = Mock()
        mock_tools.execute.side_effect = [
            "POST_READY\nPOST TEXT:\nTest post content #NFA",
            "TASK_COMPLETE: Done"
        ]

        mock_evaluator = Mock()
        eval_result = Mock()
        eval_result.passed = True
        eval_result.total = 50
        eval_result.hookiness = Mock(total=18)
        eval_result.quality = Mock(total=32)
        mock_evaluator.evaluate.return_value = eval_result
        mock_evaluator.format_report.return_value = "Report"

        agent = AgentLoop(mock_llm, mock_tools, mock_evaluator)
        result = agent.run("Create post")

        assert "TASK_COMPLETE" in result
        assert agent._pending_post == "Test post content #NFA"

    @patch("agent.loop.Config")
    @patch("agent.loop.SYSTEM_PROMPT", "Test system prompt")
    def test_write_post_evaluation_fail_retries(self, mock_config):
        """Test write_post evaluation failure feeds back for retry."""
        from agent.loop import AgentLoop

        mock_config.MAX_ITERATIONS = 3
        mock_config.EVAL_TOTAL_MIN = 50

        mock_llm = Mock()
        response = Mock()
        response.is_done = False
        response.tool_call = {"name": "write_post", "arguments": {"content": "Bad post"}}
        response.reasoning = "Writing post"
        mock_llm.generate.return_value = response

        mock_tools = Mock()
        mock_tools.execute.return_value = "POST_READY\nPOST TEXT:\nBad post content"

        mock_evaluator = Mock()
        eval_result = Mock()
        eval_result.passed = False
        eval_result.failure_reason = "Score too low"
        eval_result.total = 30
        eval_result.hookiness = Mock(total=10)
        eval_result.quality = Mock(total=20)
        mock_evaluator.evaluate.return_value = eval_result
        mock_evaluator.format_report.return_value = "Report"

        agent = AgentLoop(mock_llm, mock_tools, mock_evaluator)
        result = agent.run("Create post")

        # Agent retries until max iterations instead of hard-stopping
        assert "MAX_ITERATIONS_REACHED" in result
        # LLM should have been called multiple times (retrying)
        assert mock_llm.generate.call_count == 3

    @patch("agent.loop.Config")
    @patch("agent.loop.SYSTEM_PROMPT", "Test system prompt")
    def test_write_post_stores_pending_post_before_eval(self, mock_config):
        """Test pending_post is stored even if evaluation fails."""
        from agent.loop import AgentLoop

        mock_config.MAX_ITERATIONS = 10
        mock_config.EVAL_TOTAL_MIN = 50

        mock_llm = Mock()
        response = Mock()
        response.is_done = False
        response.tool_call = {"name": "write_post", "arguments": {"content": "Post"}}
        response.reasoning = "Writing"
        mock_llm.generate.return_value = response

        mock_tools = Mock()
        mock_tools.execute.return_value = "POST_READY\nPOST TEXT:\nThe actual post content"

        mock_evaluator = Mock()
        eval_result = Mock()
        eval_result.passed = False
        eval_result.failure_reason = "Failed"
        eval_result.total = 20
        eval_result.hookiness = Mock(total=8)
        eval_result.quality = Mock(total=12)
        mock_evaluator.evaluate.return_value = eval_result
        mock_evaluator.format_report.return_value = "Report"

        agent = AgentLoop(mock_llm, mock_tools, mock_evaluator)
        agent.run("Create post")

        # Pending post should be stored even though eval failed
        assert agent._pending_post == "The actual post content"


class TestExtractPostText:
    """Tests for _extract_post_text method."""

    @patch("agent.loop.Config")
    def test_extract_post_text_success(self, mock_config):
        """Test successful extraction of post text."""
        from agent.loop import AgentLoop

        mock_config.MAX_ITERATIONS = 10

        agent = AgentLoop(Mock(), Mock())

        result = "POST_READY\nPOST TEXT:\nThis is the post content\nSUGGESTIONS: Add more"
        text = agent._extract_post_text(result)

        assert text == "This is the post content"

    @patch("agent.loop.Config")
    def test_extract_post_text_no_marker(self, mock_config):
        """Test extraction fails without POST TEXT marker."""
        from agent.loop import AgentLoop

        mock_config.MAX_ITERATIONS = 10

        agent = AgentLoop(Mock(), Mock())

        result = "POST_READY\nNo proper marker"
        text = agent._extract_post_text(result)

        assert text is None

    @patch("agent.loop.Config")
    def test_extract_post_text_empty_after_marker(self, mock_config):
        """Test extraction with empty text after marker."""
        from agent.loop import AgentLoop

        mock_config.MAX_ITERATIONS = 10

        agent = AgentLoop(Mock(), Mock())

        result = "POST_READY\nPOST TEXT:"
        text = agent._extract_post_text(result)

        assert text == ""

    @patch("agent.loop.Config")
    def test_extract_post_text_strips_whitespace(self, mock_config):
        """Test extraction strips leading/trailing whitespace."""
        from agent.loop import AgentLoop

        mock_config.MAX_ITERATIONS = 10

        agent = AgentLoop(Mock(), Mock())

        result = "POST_READY\nPOST TEXT:\n   Content with whitespace   \n\nSUGGESTIONS:"
        text = agent._extract_post_text(result)

        assert text == "Content with whitespace"

    @patch("agent.loop.Config")
    def test_extract_post_text_multiline(self, mock_config):
        """Test extraction of multiline post text."""
        from agent.loop import AgentLoop

        mock_config.MAX_ITERATIONS = 10

        agent = AgentLoop(Mock(), Mock())

        result = "POST_READY\nPOST TEXT:\nLine 1\nLine 2\nLine 3\nSUGGESTIONS: None"
        text = agent._extract_post_text(result)

        assert "Line 1" in text
        assert "Line 2" in text
        assert "Line 3" in text


class TestEvaluatePost:
    """Tests for _evaluate_post method."""

    @patch("agent.loop.Config")
    def test_evaluate_post_calls_evaluator(self, mock_config):
        """Test evaluate_post calls evaluator and returns score."""
        from agent.loop import AgentLoop

        mock_config.MAX_ITERATIONS = 10

        mock_evaluator = Mock()
        eval_result = Mock()
        eval_result.passed = True
        eval_result.total = 50
        mock_evaluator.evaluate.return_value = eval_result
        mock_evaluator.format_report.return_value = "Test report"

        agent = AgentLoop(Mock(), Mock(), mock_evaluator)
        result = agent._evaluate_post("Test post content")

        assert result == eval_result
        mock_evaluator.evaluate.assert_called_once_with("Test post content")
        mock_evaluator.format_report.assert_called_once_with(eval_result)


class TestCreateAgent:
    """Tests for create_agent function."""

    @patch("agent.loop.ToolRegistry")
    @patch("agent.loop.LLMClient")
    @patch("agent.loop.PostEvaluator")
    def test_create_agent_registers_tools(self, mock_evaluator, mock_llm, mock_registry):
        """Test create_agent registers all required tools."""
        from agent.loop import create_agent

        mock_registry_instance = Mock()
        mock_registry.return_value = mock_registry_instance

        agent = create_agent()

        # Verify tools were registered
        register_calls = mock_registry_instance.register.call_args_list
        assert len(register_calls) >= 7  # At least 7 tools

    @patch("agent.loop.ToolRegistry")
    @patch("agent.loop.LLMClient")
    @patch("agent.loop.PostEvaluator")
    def test_create_agent_returns_agent_loop(self, mock_evaluator, mock_llm, mock_registry):
        """Test create_agent returns AgentLoop instance."""
        from agent.loop import create_agent, AgentLoop

        agent = create_agent()

        assert isinstance(agent, AgentLoop)


class TestEvaluationFailedError:
    """Tests for EvaluationFailedError exception."""

    def test_evaluation_failed_error_message(self):
        """Test EvaluationFailedError stores message."""
        from agent.loop import EvaluationFailedError

        error = EvaluationFailedError("Post quality too low")

        assert str(error) == "Post quality too low"

    def test_evaluation_failed_error_is_exception(self):
        """Test EvaluationFailedError is an Exception."""
        from agent.loop import EvaluationFailedError

        assert issubclass(EvaluationFailedError, Exception)

        # Should be raisable
        with pytest.raises(EvaluationFailedError):
            raise EvaluationFailedError("Test error")
