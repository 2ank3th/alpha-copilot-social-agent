"""Main agent loop implementation with native Gemini function calling."""

import logging
from typing import Optional, List, Any

from google.genai import types

from .llm import LLMClient, LLMResponse
from .config import Config
from .eval import PostEvaluator
from tools.registry import ToolRegistry
from prompts.system import SYSTEM_PROMPT

logger = logging.getLogger(__name__)


class EvaluationFailedError(Exception):
    """Raised when post fails quality evaluation."""
    pass


class AgentLoop:
    """
    Main agent loop following the ReAct pattern.

    The loop:
    1. LLM reasons about current state
    2. LLM selects a tool to call
    3. Execute tool, get result
    4. Add result to context
    5. Repeat until done or max iterations
    """

    def __init__(self, llm: LLMClient, tools: ToolRegistry, evaluator: PostEvaluator = None):
        self.llm = llm
        self.tools = tools
        self.evaluator = evaluator or PostEvaluator()
        self.max_iterations = Config.MAX_ITERATIONS
        self._pending_post = None  # Track post awaiting evaluation

    def run(self, task: str) -> str:
        """
        Run the agent loop until task complete or max iterations.

        Uses native Gemini function calling for reliable tool execution.
        Properly preserves thought signatures across conversation turns.

        Args:
            task: The task description for the agent

        Returns:
            Final result or error message
        """
        logger.info(f"Starting agent loop for task: {task}")

        # Clear any pending post from previous runs
        self._pending_post = None

        # Build initial contents with system instruction and user task
        # System prompt is passed as the first content, then user message
        contents: List[Any] = [
            types.Content(
                role="user",
                parts=[types.Part.from_text(text=f"{SYSTEM_PROMPT}\n\n---\n\nTask: {task}")]
            )
        ]

        for iteration in range(1, self.max_iterations + 1):
            logger.info(f"Iteration {iteration}/{self.max_iterations}")

            try:
                # 1. Get LLM response with native function calling
                response: LLMResponse = self.llm.generate(
                    contents,
                    tools=self.tools.get_schemas()
                )

                logger.info(f"LLM reasoning: {response.reasoning[:100]}...")

                # 2. Check if done
                if response.is_done and response.tool_call:
                    # Execute done tool to get summary
                    result = self.tools.execute(
                        response.tool_call["name"],
                        **response.tool_call["arguments"]
                    )
                    logger.info(f"Task complete: {result}")
                    return result

                # 3. Execute tool if called
                if response.tool_call:
                    tool_name = response.tool_call["name"]
                    tool_args = response.tool_call["arguments"]

                    logger.info(f"Executing tool: {tool_name} with args: {tool_args}")

                    try:
                        result = self.tools.execute(tool_name, **tool_args)

                        # Evaluation gate for write_post
                        if tool_name == "write_post" and "POST_READY" in result:
                            post_text = self._extract_post_text(result)
                            if post_text:
                                # Store post BEFORE evaluation so it's accessible even if eval fails
                                self._pending_post = post_text

                                eval_result = self._evaluate_post(post_text)
                                if not eval_result.passed:
                                    # Evaluation failed - abort
                                    raise EvaluationFailedError(
                                        f"Post quality check failed: {eval_result.failure_reason}\n\n"
                                        f"Score: {eval_result.total}/75 (min {Config.EVAL_TOTAL_MIN})\n"
                                        f"Hookiness: {eval_result.hookiness.total}/25\n"
                                        f"Quality: {eval_result.quality.total}/50\n\n"
                                        "Post was NOT published. Please try a different approach."
                                    )
                                result = result + f"\n\nEVAL_PASSED: Score {eval_result.total}/75"

                        logger.info(f"Tool result: {result[:200]}...")
                    except EvaluationFailedError as e:
                        # Evaluation failure - surface to user, don't retry
                        logger.error(f"Evaluation failed: {e}")
                        return f"EVAL_FAILED: {str(e)}"
                    except Exception as e:
                        result = f"TOOL_ERROR: {str(e)}"
                        logger.error(f"Tool execution failed: {e}")

                    # 4. Add model response to context (preserves thought signatures)
                    if response.raw_content:
                        contents.append(response.raw_content)
                    else:
                        # Fallback if raw_content not available
                        contents.append(types.Content(
                            role="model",
                            parts=[types.Part.from_function_call(
                                name=tool_name,
                                args=tool_args
                            )]
                        ))

                    # 5. Add function response
                    contents.append(types.Content(
                        role="user",
                        parts=[types.Part.from_function_response(
                            name=tool_name,
                            response={"result": result}
                        )]
                    ))
                else:
                    # No tool call - add model's text response and continue
                    if response.raw_content:
                        contents.append(response.raw_content)
                    else:
                        contents.append(types.Content(
                            role="model",
                            parts=[types.Part.from_text(text=response.reasoning)]
                        ))

                    # Add a nudge to use tools
                    contents.append(types.Content(
                        role="user",
                        parts=[types.Part.from_text(
                            text="Please use one of the available tools to make progress on the task."
                        )]
                    ))

            except Exception as e:
                logger.exception(f"Error in iteration {iteration}")
                # Add error as user message
                contents.append(types.Content(
                    role="user",
                    parts=[types.Part.from_text(text=f"ERROR: {str(e)}. Please try a different approach.")]
                ))

        # Max iterations reached
        logger.warning("Max iterations reached without completion")
        return "MAX_ITERATIONS_REACHED: The agent did not complete the task within the allowed iterations."

    def _extract_post_text(self, tool_result: str) -> Optional[str]:
        """Extract post text from write_post tool result."""
        if "POST TEXT:" not in tool_result:
            return None

        parts = tool_result.split("POST TEXT:")
        if len(parts) < 2:
            return None

        # Extract text between "POST TEXT:" and any warnings/suggestions
        post_section = parts[1]
        if "SUGGESTIONS:" in post_section:
            post_section = post_section.split("SUGGESTIONS:")[0]

        return post_section.strip()

    def _evaluate_post(self, post_text: str):
        """Evaluate post and log results."""
        score = self.evaluator.evaluate(post_text)

        # Log full report
        report = self.evaluator.format_report(score)
        logger.info(f"\n{report}")

        return score


def create_agent() -> AgentLoop:
    """Create and configure the agent with all tools."""
    from tools.alpha_copilot import QueryAlphaCopilotTool
    from tools.write import WritePostTool
    from tools.market_news import GetMarketNewsTool
    from tools.publish import (
        PublishTool,
        CheckRecentPostsTool,
        GetPlatformStatusTool,
        CrossPostTool,
        DoneTool,
    )

    # Initialize LLM
    llm = LLMClient()

    # Initialize tool registry
    tools = ToolRegistry()
    tools.register(GetMarketNewsTool())  # Get LIVE news via Google Search
    tools.register(QueryAlphaCopilotTool())
    tools.register(WritePostTool())  # LLM writes complete post text
    tools.register(PublishTool())
    tools.register(CrossPostTool())  # Cross-post to Twitter + Threads
    tools.register(CheckRecentPostsTool())
    tools.register(GetPlatformStatusTool())
    tools.register(DoneTool())

    # Initialize evaluator
    evaluator = PostEvaluator()

    return AgentLoop(llm, tools, evaluator)
