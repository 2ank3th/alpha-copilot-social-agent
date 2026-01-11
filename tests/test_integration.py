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


class TestLLMPromptBuilding:
    """Test prompt building for LLM."""

    @pytest.fixture
    def llm_client(self):
        """Create LLM client with mocked Gemini client."""
        with patch.object(Config, 'GEMINI_API_KEY', 'test-key'):
            with patch('agent.llm.genai.Client'):
                client = LLMClient(enable_grounding=False)
                return client

    def test_build_prompt_includes_system_message(self, llm_client):
        """Test prompt includes system message."""
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Hello"}
        ]
        tools = []

        prompt = llm_client._build_prompt_with_tools(messages, tools)

        assert "You are a helpful assistant." in prompt
        assert "USER: Hello" in prompt

    def test_build_prompt_includes_tool_descriptions(self, llm_client):
        """Test prompt includes tool descriptions."""
        messages = [{"role": "user", "content": "Test"}]
        tools = [
            {
                "name": "test_tool",
                "description": "A test tool for testing",
                "parameters": {
                    "properties": {
                        "arg1": {"type": "string", "description": "First argument"}
                    },
                    "required": ["arg1"]
                }
            }
        ]

        prompt = llm_client._build_prompt_with_tools(messages, tools)

        assert "test_tool" in prompt
        assert "A test tool for testing" in prompt
        assert "arg1" in prompt
        assert "(required)" in prompt

    def test_build_prompt_handles_conversation_history(self, llm_client):
        """Test prompt includes full conversation history."""
        messages = [
            {"role": "system", "content": "System prompt"},
            {"role": "user", "content": "User message 1"},
            {"role": "assistant", "content": "Assistant response"},
            {"role": "tool", "content": "Tool result here"},
            {"role": "user", "content": "User message 2"}
        ]
        tools = []

        prompt = llm_client._build_prompt_with_tools(messages, tools)

        assert "USER: User message 1" in prompt
        assert "ASSISTANT: Assistant response" in prompt
        assert "TOOL RESULT:\nTool result here" in prompt
        assert "USER: User message 2" in prompt

    def test_build_prompt_handles_optional_parameters(self, llm_client):
        """Test prompt marks optional parameters correctly."""
        messages = [{"role": "user", "content": "Test"}]
        tools = [
            {
                "name": "tool_with_optional",
                "description": "Tool with optional param",
                "parameters": {
                    "properties": {
                        "required_arg": {"type": "string", "description": "Required"},
                        "optional_arg": {"type": "integer", "description": "Optional"}
                    },
                    "required": ["required_arg"]
                }
            }
        ]

        prompt = llm_client._build_prompt_with_tools(messages, tools)

        assert "required_arg" in prompt
        assert "(required)" in prompt
        assert "optional_arg" in prompt
        assert "(optional)" in prompt


class TestLLMResponseParsing:
    """Test LLM response parsing for various formats."""

    @pytest.fixture
    def llm_client(self):
        """Create LLM client with mocked Gemini client."""
        with patch.object(Config, 'GEMINI_API_KEY', 'test-key'):
            with patch('agent.llm.genai.Client'):
                client = LLMClient(enable_grounding=False)
                return client

    def test_parse_json_with_backticks(self, llm_client):
        """Test parsing JSON wrapped in triple backticks."""
        text = '''Here's my reasoning.

```json
{"tool": "write_post", "arguments": {"post_text": "Test post", "platform": "twitter"}}
```
'''
        result = llm_client._parse_response(text)

        assert result.tool_call is not None
        assert result.tool_call["name"] == "write_post"
        assert result.tool_call["arguments"]["post_text"] == "Test post"
        assert result.tool_call["arguments"]["platform"] == "twitter"

    def test_parse_json_without_backticks(self, llm_client):
        """Test parsing JSON without backticks (json\\n{...} format)."""
        text = '''json
{"tool": "get_market_news", "arguments": {}}'''
        result = llm_client._parse_response(text)

        assert result.tool_call is not None
        assert result.tool_call["name"] == "get_market_news"

    def test_parse_inline_json(self, llm_client):
        """Test parsing inline JSON without any formatting."""
        text = 'I will call {"tool": "done", "arguments": {"summary": "Task complete"}} now.'
        result = llm_client._parse_response(text)

        assert result.tool_call is not None
        assert result.tool_call["name"] == "done"
        assert result.tool_call["arguments"]["summary"] == "Task complete"

    def test_parse_done_tool_sets_is_done(self, llm_client):
        """Test that parsing 'done' tool sets is_done flag."""
        text = '```json\n{"tool": "done", "arguments": {"summary": "Completed"}}\n```'
        result = llm_client._parse_response(text)

        assert result.is_done is True

    def test_parse_no_tool_call(self, llm_client):
        """Test parsing response with no tool call."""
        text = "I'm thinking about what to do next..."
        result = llm_client._parse_response(text)

        assert result.tool_call is None
        assert result.is_done is False

    def test_parse_malformed_json_fallback(self, llm_client):
        """Test that malformed JSON falls back gracefully."""
        text = '{"tool": "write_post", arguments: invalid}'
        result = llm_client._parse_response(text)

        # Should not crash, returns None tool_call
        assert result.tool_call is None

    def test_parse_nested_json_in_post_text(self, llm_client):
        """Test parsing JSON where post_text contains special characters."""
        text = '''```json
{"tool": "write_post", "arguments": {"post_text": "$NVDA up 10%! → Sell $950 call\\n#NVDA #NFA", "platform": "twitter"}}
```'''
        result = llm_client._parse_response(text)

        assert result.tool_call is not None
        assert "$NVDA" in result.tool_call["arguments"]["post_text"]

    def test_parse_inline_json_with_brace_matching(self, llm_client):
        """Test inline JSON parsing with brace depth matching."""
        text = 'I will execute {"tool": "query_alpha_copilot", "arguments": {"query": "Find options for NVDA"}} to get data.'
        result = llm_client._parse_response(text)

        assert result.tool_call is not None
        assert result.tool_call["name"] == "query_alpha_copilot"
        assert result.tool_call["arguments"]["query"] == "Find options for NVDA"

    def test_parse_json_with_nested_objects(self, llm_client):
        """Test parsing JSON with nested objects in arguments."""
        text = '''```json
{"tool": "complex_tool", "arguments": {"config": {"nested": "value"}, "simple": "arg"}}
```'''
        result = llm_client._parse_response(text)

        assert result.tool_call is not None
        assert result.tool_call["arguments"]["config"]["nested"] == "value"


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
        # Mock LLM to return done tool call
        mock_llm.generate.return_value = LLMResponse(
            reasoning="Task complete",
            tool_call={"name": "done", "arguments": {"summary": "Posted successfully"}},
            is_done=True
        )

        agent = AgentLoop(mock_llm, mock_tools, mock_evaluator)
        result = agent.run("Test task")

        assert "TASK_COMPLETE" in result
        assert "Posted successfully" in result

    def test_agent_executes_write_post_with_evaluation(self, mock_llm, mock_tools, mock_evaluator):
        """Test that write_post triggers evaluation."""
        good_post = "$NVDA up 10%!\n→ Sell $950 call\n→ $12 premium\n→ 75% POP\n#NVDA #NFA"

        # First call: write_post, second call: done
        mock_llm.generate.side_effect = [
            LLMResponse(
                reasoning="Writing post",
                tool_call={"name": "write_post", "arguments": {"post_text": good_post, "platform": "twitter"}},
                is_done=False
            ),
            LLMResponse(
                reasoning="Done",
                tool_call={"name": "done", "arguments": {"summary": "Posted"}},
                is_done=True
            )
        ]

        agent = AgentLoop(mock_llm, mock_tools, mock_evaluator)
        result = agent.run("Create a post")

        # Verify evaluation was called
        mock_evaluator.evaluate.assert_called_once()
        assert "TASK_COMPLETE" in result

    def test_agent_fails_on_low_evaluation(self, mock_llm, mock_tools):
        """Test that agent returns EVAL_FAILED on low score."""
        # Create evaluator that fails
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
        mock_llm.generate.return_value = LLMResponse(
            reasoning="Writing post",
            tool_call={"name": "write_post", "arguments": {"post_text": bad_post, "platform": "twitter"}},
            is_done=False
        )

        agent = AgentLoop(mock_llm, mock_tools, failing_evaluator)
        result = agent.run("Create a post")

        assert "EVAL_FAILED" in result

    def test_agent_respects_max_iterations(self, mock_llm, mock_tools, mock_evaluator):
        """Test that agent stops at max iterations."""
        # Mock LLM to never return done
        mock_llm.generate.return_value = LLMResponse(
            reasoning="Still thinking...",
            tool_call=None,
            is_done=False
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
