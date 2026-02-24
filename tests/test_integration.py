"""Integration tests for module interactions.

These tests use mocks to test module integration without external APIs.
They focus on:
- LLM response parsing and tool call extraction
- Agent loop execution with mocked LLM responses
- Tool registry and execution flow
- Platform publishing pipeline
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import json

from agent.llm import LLMClient, LLMResponse
from agent.loop import AgentLoop, EvaluationFailedError
from agent.eval import PostEvaluator, UnifiedScore, HookinessScore, QualityScore
from agent.config import Config
from tools.registry import ToolRegistry
from tools.write import WritePostTool
from tools.publish import PublishTool, CheckRecentPostsTool, DoneTool
from platforms.twitter import TwitterPlatform
from platforms.threads import ThreadsPlatform


class TestLLMClientInitialization:
    """Test LLM client initialization."""

    def test_raises_without_api_key(self):
        """Test that LLMClient raises ValueError without API key."""
        with patch.object(Config, 'GEMINI_API_KEY', None):
            with pytest.raises(ValueError, match="GEMINI_API_KEY not configured"):
                LLMClient()

    def test_initializes_with_grounding(self):
        """Test LLMClient initializes with grounding enabled."""
        with patch.object(Config, 'GEMINI_API_KEY', 'test-key'):
            with patch('agent.llm.genai.Client'):
                client = LLMClient(enable_grounding=True)
                assert client.enable_grounding is True
                assert client.grounding_tool is not None

    def test_initializes_without_grounding(self):
        """Test LLMClient initializes with grounding disabled."""
        with patch.object(Config, 'GEMINI_API_KEY', 'test-key'):
            with patch('agent.llm.genai.Client'):
                client = LLMClient(enable_grounding=False)
                assert client.enable_grounding is False
                assert client.grounding_tool is None


class TestFunctionDeclarationConversion:
    """Test conversion of tool schemas to Gemini function declarations."""

    @pytest.fixture
    def llm_client(self):
        """Create LLM client with mocked Gemini client."""
        with patch.object(Config, 'GEMINI_API_KEY', 'test-key'):
            with patch('agent.llm.genai.Client'):
                client = LLMClient(enable_grounding=False)
                return client

    def test_convert_simple_tool(self, llm_client):
        """Test converting a simple tool schema."""
        tools = [
            {
                "name": "test_tool",
                "description": "A test tool for testing",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "arg1": {"type": "string", "description": "First argument"}
                    },
                    "required": ["arg1"]
                }
            }
        ]

        declarations = llm_client._convert_to_function_declarations(tools)

        assert len(declarations) == 1
        assert declarations[0].name == "test_tool"
        assert declarations[0].description == "A test tool for testing"

    def test_convert_multiple_tools(self, llm_client):
        """Test converting multiple tool schemas."""
        tools = [
            {"name": "tool1", "description": "First tool", "parameters": {}},
            {"name": "tool2", "description": "Second tool", "parameters": {}},
            {"name": "tool3", "description": "Third tool", "parameters": {}}
        ]

        declarations = llm_client._convert_to_function_declarations(tools)

        assert len(declarations) == 3
        assert declarations[0].name == "tool1"
        assert declarations[1].name == "tool2"
        assert declarations[2].name == "tool3"

    def test_convert_tool_with_optional_params(self, llm_client):
        """Test converting tool with optional parameters."""
        tools = [
            {
                "name": "tool_with_optional",
                "description": "Tool with optional param",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "required_arg": {"type": "string", "description": "Required"},
                        "optional_arg": {"type": "integer", "description": "Optional"}
                    },
                    "required": ["required_arg"]
                }
            }
        ]

        declarations = llm_client._convert_to_function_declarations(tools)

        assert len(declarations) == 1
        assert declarations[0].name == "tool_with_optional"

    def test_convert_tool_without_params(self, llm_client):
        """Test converting tool without parameters."""
        tools = [
            {"name": "no_params_tool", "description": "Tool with no params"}
        ]

        declarations = llm_client._convert_to_function_declarations(tools)

        assert len(declarations) == 1
        assert declarations[0].name == "no_params_tool"
        assert declarations[0].parameters is None


class TestNativeResponseParsing:
    """Test native Gemini response parsing."""

    @pytest.fixture
    def llm_client(self):
        """Create LLM client with mocked Gemini client."""
        with patch.object(Config, 'GEMINI_API_KEY', 'test-key'):
            with patch('agent.llm.genai.Client'):
                client = LLMClient(enable_grounding=False)
                return client

    def test_parse_function_call_response(self, llm_client):
        """Test parsing response with function call."""
        mock_function_call = Mock()
        mock_function_call.name = "write_post"
        mock_function_call.args = {"post_text": "Test post", "platform": "twitter"}

        mock_part = Mock()
        mock_part.function_call = mock_function_call
        mock_part.text = None

        mock_content = Mock()
        mock_content.parts = [mock_part]

        mock_candidate = Mock()
        mock_candidate.content = mock_content

        mock_response = Mock()
        mock_response.candidates = [mock_candidate]

        result = llm_client._parse_native_response(mock_response)

        assert result.tool_call is not None
        assert result.tool_call["name"] == "write_post"
        assert result.tool_call["arguments"]["post_text"] == "Test post"

    def test_parse_text_response(self, llm_client):
        """Test parsing response with text only."""
        mock_part = Mock()
        mock_part.function_call = None
        mock_part.text = "I'm thinking about what to do next..."

        mock_content = Mock()
        mock_content.parts = [mock_part]

        mock_candidate = Mock()
        mock_candidate.content = mock_content

        mock_response = Mock()
        mock_response.candidates = [mock_candidate]

        result = llm_client._parse_native_response(mock_response)

        assert result.tool_call is None
        assert result.is_done is False
        assert "thinking" in result.reasoning

    def test_parse_done_tool_sets_is_done(self, llm_client):
        """Test that parsing 'done' function call sets is_done flag."""
        mock_function_call = Mock()
        mock_function_call.name = "done"
        mock_function_call.args = {"summary": "Task complete"}

        mock_part = Mock()
        mock_part.function_call = mock_function_call
        mock_part.text = None

        mock_content = Mock()
        mock_content.parts = [mock_part]

        mock_candidate = Mock()
        mock_candidate.content = mock_content

        mock_response = Mock()
        mock_response.candidates = [mock_candidate]

        result = llm_client._parse_native_response(mock_response)

        assert result.is_done is True
        assert result.tool_call["name"] == "done"

    def test_parse_empty_response(self, llm_client):
        """Test parsing response with no candidates."""
        mock_response = Mock()
        mock_response.candidates = []

        result = llm_client._parse_native_response(mock_response)

        assert result.tool_call is None
        assert "No response" in result.reasoning

    def test_parse_response_preserves_raw_content(self, llm_client):
        """Test that parsing preserves raw content for thought signatures."""
        mock_part = Mock()
        mock_part.function_call = None
        mock_part.text = "Reasoning text"

        mock_content = Mock()
        mock_content.parts = [mock_part]

        mock_candidate = Mock()
        mock_candidate.content = mock_content

        mock_response = Mock()
        mock_response.candidates = [mock_candidate]

        result = llm_client._parse_native_response(mock_response)

        assert result.raw_content == mock_content

    def test_parse_mixed_text_and_function_call(self, llm_client):
        """Test parsing response with both text and function call parts."""
        mock_text_part = Mock()
        mock_text_part.function_call = None
        mock_text_part.text = "Let me search for information."

        mock_function_call = Mock()
        mock_function_call.name = "get_market_news"
        mock_function_call.args = {}

        mock_fc_part = Mock()
        mock_fc_part.function_call = mock_function_call
        mock_fc_part.text = None

        mock_content = Mock()
        mock_content.parts = [mock_text_part, mock_fc_part]

        mock_candidate = Mock()
        mock_candidate.content = mock_content

        mock_response = Mock()
        mock_response.candidates = [mock_candidate]

        result = llm_client._parse_native_response(mock_response)

        assert result.tool_call is not None
        assert result.tool_call["name"] == "get_market_news"
        assert "search for information" in result.reasoning


class TestLLMGroundingSources:
    """Test grounding sources extraction."""

    @pytest.fixture
    def llm_client(self):
        """Create LLM client with mocked Gemini client."""
        with patch.object(Config, 'GEMINI_API_KEY', 'test-key'):
            with patch('agent.llm.genai.Client'):
                client = LLMClient(enable_grounding=False)
                return client

    def test_extract_grounding_sources_with_metadata(self, llm_client):
        """Test extracting grounding sources from response with metadata."""
        # Create mock response with grounding metadata
        mock_chunk = Mock()
        mock_chunk.web = Mock()
        mock_chunk.web.uri = "https://example.com/article"
        mock_chunk.web.title = "Example Article"

        mock_metadata = Mock()
        mock_metadata.grounding_chunks = [mock_chunk]
        mock_metadata.web_search_queries = ["test query"]

        mock_candidate = Mock()
        mock_candidate.grounding_metadata = mock_metadata

        mock_response = Mock()
        mock_response.candidates = [mock_candidate]

        sources = llm_client._extract_grounding_sources(mock_response)

        assert sources is not None
        assert len(sources) == 1
        assert "Example Article" in sources[0]
        assert "https://example.com/article" in sources[0]

    def test_extract_grounding_sources_without_metadata(self, llm_client):
        """Test extracting grounding sources when no metadata present."""
        mock_response = Mock()
        mock_response.candidates = []

        sources = llm_client._extract_grounding_sources(mock_response)

        assert sources is None

    def test_extract_grounding_sources_handles_exceptions(self, llm_client):
        """Test grounding source extraction handles exceptions gracefully."""
        mock_response = Mock()
        mock_response.candidates = Mock(side_effect=Exception("Test error"))

        # Should not raise, just return None
        sources = llm_client._extract_grounding_sources(mock_response)

        assert sources is None

    def test_extract_grounding_uri_without_title(self, llm_client):
        """Test extracting URI when title is not present."""
        mock_chunk = Mock()
        mock_chunk.web = Mock()
        mock_chunk.web.uri = "https://example.com/no-title"
        mock_chunk.web.title = None

        mock_metadata = Mock()
        mock_metadata.grounding_chunks = [mock_chunk]
        mock_metadata.web_search_queries = None

        mock_candidate = Mock()
        mock_candidate.grounding_metadata = mock_metadata

        mock_response = Mock()
        mock_response.candidates = [mock_candidate]

        sources = llm_client._extract_grounding_sources(mock_response)

        assert sources is not None
        assert sources[0] == "https://example.com/no-title"


class TestAgentLoopIntegration:
    """Test agent loop with mocked components."""

    @pytest.fixture
    def mock_llm(self):
        """Create a mock LLM client."""
        return Mock(spec=LLMClient)

    @pytest.fixture
    def mock_tools(self):
        """Create a mock tool registry with basic tools."""
        registry = ToolRegistry()

        # Add real tools for testing
        registry.register(WritePostTool())
        registry.register(DoneTool())

        return registry

    @pytest.fixture
    def mock_evaluator(self):
        """Create a mock evaluator that always passes."""
        evaluator = Mock(spec=PostEvaluator)
        evaluator.evaluate.return_value = UnifiedScore(
            hookiness=HookinessScore(
                post="test", news_hook=4, specificity=4, urgency=3,
                human_voice=4, scroll_stop=4, total=19, reasoning="Good"
            ),
            quality=QualityScore(
                thesis_clarity=8, news_driven=7, actionable=8,
                engagement=7, originality=6, total=36, reasoning="Good"
            ),
            total=55,
            passed=True,
            failure_reason=""
        )
        evaluator.format_report.return_value = "PASS: 55/75"
        return evaluator

    def test_agent_executes_done_tool_completes(self, mock_llm, mock_tools, mock_evaluator):
        """Test that agent completes when done tool is called."""
        # Mock LLM to return done tool call with raw_content
        mock_content = Mock()
        mock_llm.generate.return_value = LLMResponse(
            reasoning="Task complete",
            tool_call={"name": "done", "arguments": {"summary": "Posted successfully"}},
            is_done=True,
            raw_content=mock_content
        )

        agent = AgentLoop(mock_llm, mock_tools, mock_evaluator)
        result = agent.run("Test task")

        assert "TASK_COMPLETE" in result
        assert "Posted successfully" in result

    def test_agent_executes_write_post_with_evaluation(self, mock_llm, mock_tools, mock_evaluator):
        """Test that write_post triggers evaluation."""
        good_post = "$NVDA up 10%!\n→ Sell $950 call\n→ $12 premium\n→ 75% POP\n#NVDA #NFA"

        # First call: write_post, second call: done (both with raw_content)
        mock_content1 = Mock()
        mock_content2 = Mock()
        mock_llm.generate.side_effect = [
            LLMResponse(
                reasoning="Writing post",
                tool_call={"name": "write_post", "arguments": {"post_text": good_post, "platform": "twitter"}},
                is_done=False,
                raw_content=mock_content1
            ),
            LLMResponse(
                reasoning="Done",
                tool_call={"name": "done", "arguments": {"summary": "Posted"}},
                is_done=True,
                raw_content=mock_content2
            )
        ]

        agent = AgentLoop(mock_llm, mock_tools, mock_evaluator)
        result = agent.run("Create a post")

        # Verify evaluation was called
        mock_evaluator.evaluate.assert_called_once()
        assert "TASK_COMPLETE" in result

    def test_agent_retries_on_low_evaluation(self, mock_llm, mock_tools):
        """Test that eval failure feeds back to agent for retry instead of hard-stopping."""
        # Create evaluator that always fails
        failing_evaluator = Mock(spec=PostEvaluator)
        failing_evaluator.evaluate.return_value = UnifiedScore(
            hookiness=HookinessScore(
                post="bad", news_hook=1, specificity=1, urgency=1,
                human_voice=1, scroll_stop=1, total=5, reasoning="Poor"
            ),
            quality=QualityScore(
                thesis_clarity=2, news_driven=2, actionable=2,
                engagement=2, originality=2, total=10, reasoning="Poor"
            ),
            total=15,
            passed=False,
            failure_reason="Score too low"
        )
        failing_evaluator.format_report.return_value = "FAIL: 15/75"

        bad_post = "AAPL $180 72% - this is a longer post to pass minimum length validation test"
        mock_content = Mock()
        mock_llm.generate.return_value = LLMResponse(
            reasoning="Writing post",
            tool_call={"name": "write_post", "arguments": {"post_text": bad_post, "platform": "twitter"}},
            is_done=False,
            raw_content=mock_content
        )

        agent = AgentLoop(mock_llm, mock_tools, failing_evaluator)
        result = agent.run("Create a post")

        # Agent should retry until max iterations, not hard-stop
        assert "MAX_ITERATIONS_REACHED" in result

    def test_agent_respects_max_iterations(self, mock_llm, mock_tools, mock_evaluator):
        """Test that agent stops at max iterations."""
        # Mock LLM to never return done (with raw_content)
        mock_content = Mock()
        mock_llm.generate.return_value = LLMResponse(
            reasoning="Still thinking...",
            tool_call=None,
            is_done=False,
            raw_content=mock_content
        )

        agent = AgentLoop(mock_llm, mock_tools, mock_evaluator)
        agent.max_iterations = 3

        result = agent.run("Never-ending task")

        assert "MAX_ITERATIONS_REACHED" in result
        assert mock_llm.generate.call_count == 3


class TestToolRegistryIntegration:
    """Test tool registry with real tools."""

    def test_registry_executes_write_post(self):
        """Test registry can execute write_post tool."""
        registry = ToolRegistry()
        registry.register(WritePostTool())

        result = registry.execute(
            "write_post",
            post_text="$NVDA up 10%! Sell $950 call, $12 premium, 75% POP #NVDA #NFA",
            platform="twitter"
        )

        assert "POST_READY" in result
        assert "twitter" in result.lower()

    def test_registry_executes_done_tool(self):
        """Test registry can execute done tool."""
        registry = ToolRegistry()
        registry.register(DoneTool())

        result = registry.execute("done", summary="Task completed successfully")

        assert "TASK_COMPLETE" in result
        assert "Task completed successfully" in result

    def test_registry_returns_schemas(self):
        """Test registry returns valid tool schemas."""
        registry = ToolRegistry()
        registry.register(WritePostTool())
        registry.register(DoneTool())

        schemas = registry.get_schemas()

        assert len(schemas) == 2
        names = [s["name"] for s in schemas]
        assert "write_post" in names
        assert "done" in names

    def test_registry_raises_for_unknown_tool(self):
        """Test registry raises for unknown tool."""
        registry = ToolRegistry()

        with pytest.raises(ValueError, match="not found"):
            registry.execute("unknown_tool")


class TestPlatformIntegration:
    """Test platform publishing integration."""

    def test_twitter_dry_run_returns_success(self):
        """Test Twitter dry-run mode."""
        with patch.object(Config, 'DRY_RUN', True):
            platform = TwitterPlatform()
            result = platform.publish("Test tweet content")

            assert result["success"] is True
            assert result["dry_run"] is True

    def test_twitter_truncates_long_content(self):
        """Test Twitter truncates content over 280 chars."""
        platform = TwitterPlatform()
        long_content = "x" * 300

        truncated = platform.truncate_content(long_content)

        assert len(truncated) <= 280
        assert truncated.endswith("...")

    def test_threads_dry_run_returns_success(self):
        """Test Threads dry-run mode."""
        with patch.object(Config, 'DRY_RUN', True):
            platform = ThreadsPlatform()
            result = platform.publish("Test threads content")

            assert result["success"] is True
            assert result["dry_run"] is True

    def test_threads_truncates_long_content(self):
        """Test Threads truncates content over 500 chars."""
        platform = ThreadsPlatform()
        long_content = "x" * 600

        truncated = platform.truncate_content(long_content)

        assert len(truncated) <= 500
        assert truncated.endswith("...")

    def test_publish_tool_routes_to_correct_platform(self):
        """Test PublishTool routes to correct platform."""
        with patch.object(Config, 'DRY_RUN', True):
            tool = PublishTool()

            twitter_result = tool.execute("Test content", "twitter")
            assert "twitter" in twitter_result.lower()
            assert "DRY_RUN" in twitter_result

    def test_check_recent_posts_handles_no_posts(self):
        """Test CheckRecentPostsTool handles empty response."""
        with patch.object(Config, 'DRY_RUN', True):
            tool = CheckRecentPostsTool()

            # Mock the platform to return empty posts
            with patch.object(TwitterPlatform, 'get_recent_posts', return_value=[]):
                result = tool.execute("twitter", hours=24)

            assert "NO_RECENT_POSTS" in result


class TestWritePostValidation:
    """Test write_post tool validation."""

    def test_validates_twitter_length(self):
        """Test post too long for Twitter is rejected."""
        tool = WritePostTool()
        long_post = "x" * 300

        result = tool.execute(long_post, "twitter")

        assert "ERROR" in result
        assert "too long" in result.lower()
        assert "280" in result

    def test_validates_threads_length(self):
        """Test post too long for Threads is rejected."""
        tool = WritePostTool()
        long_post = "x" * 600

        result = tool.execute(long_post, "threads")

        assert "ERROR" in result
        assert "too long" in result.lower()
        assert "500" in result

    def test_validates_minimum_length(self):
        """Test post too short is rejected."""
        tool = WritePostTool()
        short_post = "Hi"

        result = tool.execute(short_post, "twitter")

        assert "ERROR" in result
        assert "too short" in result.lower()

    def test_warns_missing_ticker(self):
        """Test warning for missing ticker symbol."""
        tool = WritePostTool()
        post = "Stock is up 10%! Sell call options for income. #options #NFA"

        result = tool.execute(post, "twitter")

        assert "WARNING" in result
        assert "ticker" in result.lower()

    def test_provides_shortening_tips(self):
        """Test error message provides shortening tips."""
        tool = WritePostTool()
        # Post with parenthetical company name (should suggest removing it)
        long_post = "$NVDA (Nvidia) " + "x" * 280

        result = tool.execute(long_post, "twitter")

        assert "ERROR" in result
        assert "Tips to shorten" in result
        assert "parentheses" in result.lower()


class TestEvaluatorIntegration:
    """Test evaluator with various post types."""

    def test_evaluator_passes_good_post(self, sample_good_post):
        """Test evaluator passes a well-structured post."""
        evaluator = PostEvaluator()
        score = evaluator.evaluate(sample_good_post)

        assert score.passed is True
        assert score.total >= 45

    def test_evaluator_fails_bad_post(self, sample_bad_post):
        """Test evaluator fails a poor post."""
        evaluator = PostEvaluator()
        score = evaluator.evaluate(sample_bad_post)

        assert score.passed is False
        assert score.total < 45

    def test_evaluator_format_report(self, sample_good_post):
        """Test evaluator generates readable report."""
        evaluator = PostEvaluator()
        score = evaluator.evaluate(sample_good_post)
        report = evaluator.format_report(score)

        assert "HOOKINESS" in report
        assert "QUALITY" in report
        assert "/75" in report

    def test_evaluator_detects_news_hook(self):
        """Test evaluator rewards posts with news hooks."""
        evaluator = PostEvaluator()

        news_post = "$NVDA surges 10% on AI chip demand! Here's a trade idea: Sell $950 call, $12 premium. #NVDA #NFA"
        no_news_post = "Sell $NVDA $950 call for $12 premium. 75% POP. #NVDA #NFA"

        news_score = evaluator.evaluate(news_post)
        no_news_score = evaluator.evaluate(no_news_post)

        # News post should score higher on hookiness
        assert news_score.hookiness.total >= no_news_score.hookiness.total


class TestConfigOverride:
    """Test Config.override context manager."""

    def test_override_dry_run(self):
        """Test overriding DRY_RUN setting."""
        original = Config.DRY_RUN

        with Config.override(DRY_RUN=True):
            assert Config.DRY_RUN is True

        # Should restore after context
        assert Config.DRY_RUN == original

    def test_override_max_iterations(self):
        """Test overriding MAX_ITERATIONS setting."""
        original = Config.MAX_ITERATIONS

        with Config.override(MAX_ITERATIONS=5):
            assert Config.MAX_ITERATIONS == 5

        assert Config.MAX_ITERATIONS == original


class TestConfigValidation:
    """Test Config validation methods."""

    def test_validate_llm_with_key(self):
        """Test validate_llm passes with API key."""
        with patch.object(Config, 'GEMINI_API_KEY', 'test-key'):
            assert Config.validate_llm() is True

    def test_validate_llm_missing_key(self):
        """Test validate_llm fails without API key."""
        with patch.object(Config, 'GEMINI_API_KEY', ''):
            assert Config.validate_llm() is False

    def test_validate_alpha_copilot_with_api_key(self):
        """Test validate_alpha_copilot passes with API key."""
        with patch.object(Config, 'ALPHA_COPILOT_API_KEY', 'test-key'):
            assert Config.validate_alpha_copilot() is True

    def test_validate_alpha_copilot_with_supabase(self):
        """Test validate_alpha_copilot passes with Supabase credentials."""
        with patch.object(Config, 'ALPHA_COPILOT_API_KEY', ''):
            with patch.object(Config, 'SUPABASE_URL', 'https://test.supabase.co'):
                with patch.object(Config, 'SUPABASE_ANON_KEY', 'anon-key'):
                    with patch.object(Config, 'SUPABASE_EMAIL', 'test@example.com'):
                        with patch.object(Config, 'SUPABASE_PASSWORD', 'password'):
                            assert Config.validate_alpha_copilot() is True

    def test_validate_alpha_copilot_none(self):
        """Test validate_alpha_copilot fails with no credentials."""
        with patch.object(Config, 'ALPHA_COPILOT_API_KEY', ''):
            with patch.object(Config, 'SUPABASE_URL', ''):
                with patch.object(Config, 'SUPABASE_ANON_KEY', ''):
                    with patch.object(Config, 'SUPABASE_EMAIL', ''):
                        with patch.object(Config, 'SUPABASE_PASSWORD', ''):
                            assert Config.validate_alpha_copilot() is False

    def test_validate_supabase_complete(self):
        """Test validate_supabase passes with all credentials."""
        with patch.object(Config, 'SUPABASE_URL', 'https://test.supabase.co'):
            with patch.object(Config, 'SUPABASE_ANON_KEY', 'anon-key'):
                with patch.object(Config, 'SUPABASE_EMAIL', 'test@example.com'):
                    with patch.object(Config, 'SUPABASE_PASSWORD', 'password'):
                        assert Config.validate_supabase() is True

    def test_validate_supabase_partial(self):
        """Test validate_supabase fails with partial credentials."""
        with patch.object(Config, 'SUPABASE_URL', 'https://test.supabase.co'):
            with patch.object(Config, 'SUPABASE_ANON_KEY', ''):  # Missing
                with patch.object(Config, 'SUPABASE_EMAIL', 'test@example.com'):
                    with patch.object(Config, 'SUPABASE_PASSWORD', 'password'):
                        assert Config.validate_supabase() is False

    def test_validate_twitter_complete(self):
        """Test validate_twitter passes with all credentials."""
        with patch.object(Config, 'TWITTER_API_KEY', 'key'):
            with patch.object(Config, 'TWITTER_API_SECRET', 'secret'):
                with patch.object(Config, 'TWITTER_ACCESS_TOKEN', 'token'):
                    with patch.object(Config, 'TWITTER_ACCESS_SECRET', 'secret'):
                        assert Config.validate_twitter() is True

    def test_validate_twitter_partial(self):
        """Test validate_twitter fails with partial credentials."""
        with patch.object(Config, 'TWITTER_API_KEY', 'key'):
            with patch.object(Config, 'TWITTER_API_SECRET', ''):  # Missing
                with patch.object(Config, 'TWITTER_ACCESS_TOKEN', 'token'):
                    with patch.object(Config, 'TWITTER_ACCESS_SECRET', 'secret'):
                        assert Config.validate_twitter() is False

    def test_validate_threads_complete(self):
        """Test validate_threads passes with all credentials."""
        with patch.object(Config, 'THREADS_ACCESS_TOKEN', 'token'):
            with patch.object(Config, 'THREADS_USER_ID', 'user-id'):
                assert Config.validate_threads() is True

    def test_validate_threads_partial(self):
        """Test validate_threads fails with partial credentials."""
        with patch.object(Config, 'THREADS_ACCESS_TOKEN', 'token'):
            with patch.object(Config, 'THREADS_USER_ID', ''):  # Missing
                assert Config.validate_threads() is False

    def test_get_enabled_platforms_both(self):
        """Test get_enabled_platforms returns both when configured."""
        with patch.object(Config, 'TWITTER_API_KEY', 'key'):
            with patch.object(Config, 'TWITTER_API_SECRET', 'secret'):
                with patch.object(Config, 'TWITTER_ACCESS_TOKEN', 'token'):
                    with patch.object(Config, 'TWITTER_ACCESS_SECRET', 'secret'):
                        with patch.object(Config, 'THREADS_ACCESS_TOKEN', 'token'):
                            with patch.object(Config, 'THREADS_USER_ID', 'user-id'):
                                platforms = Config.get_enabled_platforms()
                                assert "twitter" in platforms
                                assert "threads" in platforms

    def test_get_enabled_platforms_twitter_only(self):
        """Test get_enabled_platforms returns only Twitter."""
        with patch.object(Config, 'TWITTER_API_KEY', 'key'):
            with patch.object(Config, 'TWITTER_API_SECRET', 'secret'):
                with patch.object(Config, 'TWITTER_ACCESS_TOKEN', 'token'):
                    with patch.object(Config, 'TWITTER_ACCESS_SECRET', 'secret'):
                        with patch.object(Config, 'THREADS_ACCESS_TOKEN', ''):
                            with patch.object(Config, 'THREADS_USER_ID', ''):
                                platforms = Config.get_enabled_platforms()
                                assert "twitter" in platforms
                                assert "threads" not in platforms

    def test_get_enabled_platforms_none(self):
        """Test get_enabled_platforms returns empty when none configured."""
        with patch.object(Config, 'TWITTER_API_KEY', ''):
            with patch.object(Config, 'TWITTER_API_SECRET', ''):
                with patch.object(Config, 'TWITTER_ACCESS_TOKEN', ''):
                    with patch.object(Config, 'TWITTER_ACCESS_SECRET', ''):
                        with patch.object(Config, 'THREADS_ACCESS_TOKEN', ''):
                            with patch.object(Config, 'THREADS_USER_ID', ''):
                                platforms = Config.get_enabled_platforms()
                                assert platforms == []


class TestCrossPostTool:
    """Test CrossPostTool cross-posting functionality."""

    def test_cross_post_both_platforms_dry_run(self):
        """Test cross-posting to both platforms in dry-run mode."""
        from tools.publish import CrossPostTool

        with patch.object(Config, 'DRY_RUN', True):
            tool = CrossPostTool()
            result = tool.execute("Test content for cross-posting", include_promo=False)

            assert "CROSS_POST_RESULTS" in result
            assert "twitter" in result.lower()
            assert "threads" in result.lower()
            assert "DRY_RUN" in result

    def test_cross_post_with_promo_dry_run(self):
        """Test cross-posting with promotional follow-up in dry-run mode."""
        from tools.publish import CrossPostTool

        with patch.object(Config, 'DRY_RUN', True):
            with patch.object(Config, 'ENABLE_PROMO_POST', True):
                tool = CrossPostTool()
                result = tool.execute("Test content", include_promo=True)

                assert "CROSS_POST_RESULTS" in result
                assert "promo" in result.lower()

    def test_cross_post_content_formatting(self):
        """Test content is formatted for platform limits."""
        from tools.publish import CrossPostTool

        with patch.object(Config, 'DRY_RUN', True):
            tool = CrossPostTool()

            # Long content that exceeds Twitter limit
            long_content = "x" * 300
            result = tool.execute(long_content, include_promo=False)

            # Should still succeed in dry-run mode
            assert "CROSS_POST_RESULTS" in result

    def test_cross_post_uses_config_for_promo_default(self):
        """Test that include_promo defaults to Config.ENABLE_PROMO_POST."""
        from tools.publish import CrossPostTool

        with patch.object(Config, 'DRY_RUN', True):
            with patch.object(Config, 'ENABLE_PROMO_POST', False):
                tool = CrossPostTool()
                result = tool.execute("Test content")

                # Promo should not be attempted when disabled by default
                # Result should not mention promo success
                assert "CROSS_POST_RESULTS" in result


class TestAlphaCopilotTool:
    """Test Alpha Copilot tool integration."""

    def test_tool_schema(self):
        """Test Alpha Copilot tool has correct schema."""
        from tools.alpha_copilot import QueryAlphaCopilotTool

        with patch.object(Config, 'ALPHA_COPILOT_API_KEY', 'test-key'):
            with patch('tools.alpha_copilot.httpx.Client'):
                tool = QueryAlphaCopilotTool()
                schema = tool.get_schema()

                assert schema["name"] == "query_alpha_copilot"
                assert "query" in schema["parameters"]["properties"]
                assert "query" in schema["parameters"]["required"]

    def test_execute_returns_error_without_auth(self):
        """Test execute returns error without authentication."""
        from tools.alpha_copilot import QueryAlphaCopilotTool

        with patch.object(Config, 'ALPHA_COPILOT_API_KEY', ''):
            with patch.object(Config, 'SUPABASE_URL', ''):
                with patch.object(Config, 'SUPABASE_ANON_KEY', ''):
                    with patch.object(Config, 'SUPABASE_EMAIL', ''):
                        with patch.object(Config, 'SUPABASE_PASSWORD', ''):
                            with patch('tools.alpha_copilot.httpx.Client'):
                                tool = QueryAlphaCopilotTool()
                                result = tool.execute("Find options for NVDA")

                                assert "ERROR" in result

    @patch('tools.alpha_copilot.httpx.Client')
    def test_execute_with_api_key(self, mock_client_class):
        """Test execute uses API key authentication."""
        from tools.alpha_copilot import QueryAlphaCopilotTool

        mock_client = Mock()
        mock_client_class.return_value = mock_client

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "success",
            "analysis": {
                "market_overview": "Bullish sentiment",
                "recommendations": [
                    {
                        "symbol": "NVDA",
                        "strategy": "Covered Call",
                        "strike": 950,
                        "premium": 12,
                        "probability_of_profit": 75,
                        "expiration": "Jan 17",
                        "rationale": "Strong momentum"
                    }
                ]
            }
        }
        mock_response.raise_for_status = Mock()
        mock_client.post.return_value = mock_response

        with patch.object(Config, 'ALPHA_COPILOT_API_KEY', 'test-api-key'):
            with patch.object(Config, 'ALPHA_COPILOT_API_URL', 'https://api.test.com'):
                tool = QueryAlphaCopilotTool()
                result = tool.execute("Find covered calls for NVDA")

                assert "NVDA" in result
                assert "Covered Call" in result
                assert "STATUS: success" in result

    @patch('tools.alpha_copilot.httpx.Client')
    def test_execute_handles_no_recommendations(self, mock_client_class):
        """Test execute handles empty recommendations."""
        from tools.alpha_copilot import QueryAlphaCopilotTool

        mock_client = Mock()
        mock_client_class.return_value = mock_client

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "success",
            "analysis": {
                "market_overview": "No good trades",
                "recommendations": []
            }
        }
        mock_response.raise_for_status = Mock()
        mock_client.post.return_value = mock_response

        with patch.object(Config, 'ALPHA_COPILOT_API_KEY', 'test-api-key'):
            tool = QueryAlphaCopilotTool()
            result = tool.execute("Find options")

            assert "NO_RECOMMENDATIONS" in result

    @patch('tools.alpha_copilot.httpx.Client')
    def test_execute_handles_timeout(self, mock_client_class):
        """Test execute handles timeout gracefully."""
        from tools.alpha_copilot import QueryAlphaCopilotTool
        import httpx

        mock_client = Mock()
        mock_client_class.return_value = mock_client
        mock_client.post.side_effect = httpx.TimeoutException("Timeout")

        with patch.object(Config, 'ALPHA_COPILOT_API_KEY', 'test-api-key'):
            tool = QueryAlphaCopilotTool()
            result = tool.execute("Find options")

            assert "ERROR" in result
            assert "timed out" in result.lower()


class TestAgentLoopErrors:
    """Test agent loop error handling paths."""

    @pytest.fixture
    def mock_llm(self):
        """Create a mock LLM client."""
        return Mock(spec=LLMClient)

    @pytest.fixture
    def mock_tools(self):
        """Create a mock tool registry."""
        registry = ToolRegistry()
        registry.register(WritePostTool())
        registry.register(DoneTool())
        return registry

    @pytest.fixture
    def mock_evaluator(self):
        """Create a mock evaluator that always passes."""
        evaluator = Mock(spec=PostEvaluator)
        evaluator.evaluate.return_value = UnifiedScore(
            hookiness=HookinessScore(
                post="test", news_hook=4, specificity=4, urgency=3,
                human_voice=4, scroll_stop=4, total=19, reasoning="Good"
            ),
            quality=QualityScore(
                thesis_clarity=8, news_driven=7, actionable=8,
                engagement=7, originality=6, total=36, reasoning="Good"
            ),
            total=55,
            passed=True,
            failure_reason=""
        )
        evaluator.format_report.return_value = "PASS: 55/75"
        return evaluator

    def test_max_iterations_exact_boundary(self, mock_llm, mock_tools, mock_evaluator):
        """Test that agent stops at exactly max_iterations."""
        mock_content = Mock()
        mock_llm.generate.return_value = LLMResponse(
            reasoning="Thinking...",
            tool_call=None,
            is_done=False,
            raw_content=mock_content
        )

        agent = AgentLoop(mock_llm, mock_tools, mock_evaluator)
        agent.max_iterations = 5

        result = agent.run("Test task")

        assert "MAX_ITERATIONS_REACHED" in result
        assert mock_llm.generate.call_count == 5

    def test_tool_result_added_to_contents(self, mock_llm, mock_tools, mock_evaluator):
        """Test that tool results are added to conversation history as Content objects."""
        good_post = "$NVDA up 10%! Sell $950 call, $12 premium, 75% POP. #NVDA #NFA"

        # Track contents length at each call
        contents_lengths = []

        def track_contents(contents, tools):
            contents_lengths.append(len(contents))
            # Return done on second call
            if len(contents_lengths) == 1:
                return LLMResponse(
                    reasoning="Writing post",
                    tool_call={"name": "write_post", "arguments": {"post_text": good_post, "platform": "twitter"}},
                    is_done=False,
                    raw_content=Mock()
                )
            else:
                return LLMResponse(
                    reasoning="Done",
                    tool_call={"name": "done", "arguments": {"summary": "Posted"}},
                    is_done=True,
                    raw_content=Mock()
                )

        mock_llm.generate.side_effect = track_contents

        agent = AgentLoop(mock_llm, mock_tools, mock_evaluator)
        agent.run("Create a post")

        # Check that generate was called twice
        assert mock_llm.generate.call_count == 2

        # Verify contents grew between calls (tool result was added)
        assert len(contents_lengths) == 2
        assert contents_lengths[1] > contents_lengths[0], "Contents should grow after tool execution"


class TestPlatformErrors:
    """Test platform error handling."""

    def test_twitter_returns_error_without_client(self):
        """Test Twitter publish returns error without client."""
        with patch.object(Config, 'DRY_RUN', False):
            with patch.object(Config, 'TWITTER_API_KEY', ''):
                with patch.object(Config, 'TWITTER_API_SECRET', ''):
                    with patch.object(Config, 'TWITTER_ACCESS_TOKEN', ''):
                        with patch.object(Config, 'TWITTER_ACCESS_SECRET', ''):
                            platform = TwitterPlatform()
                            result = platform.publish("Test content")

                            assert result["success"] is False
                            assert "error" in result

    def test_threads_returns_error_without_credentials(self):
        """Test Threads publish returns error without credentials."""
        with patch.object(Config, 'DRY_RUN', False):
            with patch.object(Config, 'THREADS_ACCESS_TOKEN', ''):
                with patch.object(Config, 'THREADS_USER_ID', ''):
                    platform = ThreadsPlatform()
                    result = platform.publish("Test content")

                    assert result["success"] is False
                    assert "error" in result

    def test_publish_tool_handles_unsupported_platform(self):
        """Test PublishTool returns error for unsupported platform."""
        tool = PublishTool()
        result = tool.execute("Test content", "unsupported_platform")

        assert "ERROR" in result
        assert "not supported" in result.lower()

    def test_get_platform_status_returns_unavailable(self):
        """Test GetPlatformStatusTool returns unavailable for unconfigured platform."""
        from tools.publish import GetPlatformStatusTool

        with patch.object(Config, 'DRY_RUN', False):
            with patch.object(Config, 'TWITTER_API_KEY', ''):
                with patch.object(Config, 'TWITTER_API_SECRET', ''):
                    with patch.object(Config, 'TWITTER_ACCESS_TOKEN', ''):
                        with patch.object(Config, 'TWITTER_ACCESS_SECRET', ''):
                            tool = GetPlatformStatusTool()
                            result = tool.execute("twitter")

                            assert "UNAVAILABLE" in result
