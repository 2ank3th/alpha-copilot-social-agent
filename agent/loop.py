"""Main agent loop implementation."""

import logging
from typing import Optional

from .llm import LLMClient, LLMResponse
from .config import Config
from tools.registry import ToolRegistry
from prompts.system import SYSTEM_PROMPT

logger = logging.getLogger(__name__)


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

    def __init__(self, llm: LLMClient, tools: ToolRegistry):
        self.llm = llm
        self.tools = tools
        self.max_iterations = Config.MAX_ITERATIONS

    def run(self, task: str) -> str:
        """
        Run the agent loop until task complete or max iterations.

        Args:
            task: The task description for the agent

        Returns:
            Final result or error message
        """
        logger.info(f"Starting agent loop for task: {task}")

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": task}
        ]

        # Track key outputs for evaluation
        last_composed_tweet = None
        last_published_content = None

        for iteration in range(1, self.max_iterations + 1):
            logger.info(f"Iteration {iteration}/{self.max_iterations}")

            try:
                # 1. Get LLM response
                response: LLMResponse = self.llm.generate(
                    messages,
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

                    # Include composed tweet in result for evaluation
                    if last_composed_tweet:
                        result = f"{result}\n\n{last_composed_tweet}"
                    elif last_published_content:
                        result = f"{result}\n\nPUBLISHED_CONTENT:\n{last_published_content}"

                    return result

                # 3. Execute tool if called
                if response.tool_call:
                    tool_name = response.tool_call["name"]
                    tool_args = response.tool_call["arguments"]

                    logger.info(f"Executing tool: {tool_name} with args: {tool_args}")

                    # Handle google_search specially - grounding already happened
                    # during the API call, so we just note it and continue
                    if tool_name == "google_search":
                        logger.info("Google Search grounding was used - continuing with grounded context")
                        result = f"GROUNDING: Web search completed for: {tool_args.get('query', 'N/A')}. Results incorporated into context. Proceed with your analysis."
                        if response.grounding_sources:
                            result += f"\nSources: {', '.join(response.grounding_sources[:3])}"
                    else:
                        try:
                            result = self.tools.execute(tool_name, **tool_args)
                            logger.info(f"Tool result: {result[:200]}...")

                            # Track compose_post output for evaluation
                            if tool_name == "compose_post" and "COMPOSED_POST:" in result:
                                last_composed_tweet = result

                            # Track publish output
                            if tool_name == "publish":
                                last_published_content = tool_args.get("content", "")

                        except Exception as e:
                            result = f"TOOL_ERROR: {str(e)}"
                            logger.error(f"Tool execution failed: {e}")

                    # 4. Add to context
                    messages.append({
                        "role": "assistant",
                        "content": f"Called {tool_name}: {response.reasoning}"
                    })
                    messages.append({
                        "role": "tool",
                        "content": result
                    })
                else:
                    # No tool call - add reasoning and continue
                    messages.append({
                        "role": "assistant",
                        "content": response.reasoning
                    })

            except Exception as e:
                logger.exception(f"Error in iteration {iteration}")
                messages.append({
                    "role": "tool",
                    "content": f"ERROR: {str(e)}"
                })

        # Max iterations reached
        logger.warning("Max iterations reached without completion")
        return "MAX_ITERATIONS_REACHED: The agent did not complete the task within the allowed iterations."


def create_agent() -> AgentLoop:
    """Create and configure the agent with all tools."""
    from tools.alpha_copilot import QueryAlphaCopilotTool
    from tools.compose import ComposePostTool
    from tools.publish import PublishTool, CheckRecentPostsTool, GetPlatformStatusTool, DoneTool

    # Initialize LLM
    llm = LLMClient()

    # Initialize tool registry
    tools = ToolRegistry()
    tools.register(QueryAlphaCopilotTool())
    tools.register(ComposePostTool())
    tools.register(PublishTool())
    tools.register(CheckRecentPostsTool())
    tools.register(GetPlatformStatusTool())
    tools.register(DoneTool())

    return AgentLoop(llm, tools)
