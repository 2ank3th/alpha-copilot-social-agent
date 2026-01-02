"""LLM client for the agent."""

import json
import logging
import re
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

import google.generativeai as genai

from .config import Config

logger = logging.getLogger(__name__)


@dataclass
class LLMResponse:
    """Structured response from LLM."""
    reasoning: str
    tool_call: Optional[Dict[str, Any]] = None
    is_done: bool = False


class LLMClient:
    """Client for interacting with Gemini LLM using text-based tool calling."""

    def __init__(self):
        if not Config.GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY not configured")

        genai.configure(api_key=Config.GEMINI_API_KEY)
        self.model = genai.GenerativeModel(Config.LLM_MODEL)

    def generate(
        self,
        messages: List[Dict[str, str]],
        tools: List[Dict[str, Any]]
    ) -> LLMResponse:
        """
        Generate a response with tool calling via structured output.

        Args:
            messages: Conversation history
            tools: Available tool schemas

        Returns:
            LLMResponse with reasoning and optional tool call
        """
        # Build prompt with tool instructions
        prompt = self._build_prompt_with_tools(messages, tools)

        try:
            response = self.model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.7,
                    max_output_tokens=1024,
                ),
                request_options={"timeout": Config.LLM_TIMEOUT}
            )

            return self._parse_response(response.text)

        except Exception as e:
            logger.exception("LLM generation failed")
            raise

    def _build_prompt_with_tools(
        self,
        messages: List[Dict[str, str]],
        tools: List[Dict[str, Any]]
    ) -> str:
        """Build prompt with tool descriptions and calling format."""
        parts = []

        # Add system message first
        for msg in messages:
            if msg["role"] == "system":
                parts.append(msg["content"])
                break

        # Add tool instructions
        parts.append("\n## Tool Calling Format\n")
        parts.append("To call a tool, respond with JSON in this exact format:")
        parts.append("```json")
        parts.append('{"tool": "tool_name", "arguments": {"arg1": "value1"}}')
        parts.append("```")
        parts.append("\nAvailable tools:\n")

        for tool in tools:
            name = tool["name"]
            desc = tool["description"]
            params = tool.get("parameters", {}).get("properties", {})
            required = tool.get("parameters", {}).get("required", [])

            param_strs = []
            for pname, pinfo in params.items():
                req = "(required)" if pname in required else "(optional)"
                ptype = pinfo.get("type", "string")
                pdesc = pinfo.get("description", "")
                param_strs.append(f"    - {pname} ({ptype}) {req}: {pdesc}")

            parts.append(f"- **{name}**: {desc}")
            if param_strs:
                parts.append("  Parameters:")
                parts.extend(param_strs)
            parts.append("")

        parts.append("\nIMPORTANT: Always respond with a tool call JSON block. Do not just describe what you would do.")
        parts.append("\n---\n")

        # Add conversation history
        for msg in messages:
            role = msg["role"]
            content = msg["content"]

            if role == "system":
                continue  # Already added
            elif role == "user":
                parts.append(f"USER: {content}\n")
            elif role == "assistant":
                parts.append(f"ASSISTANT: {content}\n")
            elif role == "tool":
                parts.append(f"TOOL RESULT:\n{content}\n")

        parts.append("\nASSISTANT: ")

        return "\n".join(parts)

    def _parse_response(self, text: str) -> LLMResponse:
        """Parse LLM response to extract tool call."""
        # Look for JSON block
        json_match = re.search(r'```json\s*(.*?)\s*```', text, re.DOTALL)

        if json_match:
            try:
                data = json.loads(json_match.group(1))
                tool_name = data.get("tool")
                arguments = data.get("arguments", {})

                if tool_name:
                    return LLMResponse(
                        reasoning=text,
                        tool_call={
                            "name": tool_name,
                            "arguments": arguments
                        },
                        is_done=(tool_name == "done")
                    )
            except json.JSONDecodeError:
                pass

        # Try to find inline JSON
        json_patterns = [
            r'\{"tool":\s*"([^"]+)".*?\}',
            r'\{\s*"tool"\s*:\s*"([^"]+)"',
        ]

        for pattern in json_patterns:
            match = re.search(pattern, text)
            if match:
                # Try to extract the full JSON
                try:
                    # Find the start of the JSON
                    start = text.find('{"tool"')
                    if start >= 0:
                        # Find matching closing brace
                        depth = 0
                        for i, c in enumerate(text[start:]):
                            if c == '{':
                                depth += 1
                            elif c == '}':
                                depth -= 1
                                if depth == 0:
                                    json_str = text[start:start + i + 1]
                                    data = json.loads(json_str)
                                    return LLMResponse(
                                        reasoning=text,
                                        tool_call={
                                            "name": data.get("tool"),
                                            "arguments": data.get("arguments", {})
                                        },
                                        is_done=(data.get("tool") == "done")
                                    )
                except (json.JSONDecodeError, ValueError):
                    pass

        # No tool call found
        return LLMResponse(
            reasoning=text,
            tool_call=None,
            is_done=False
        )
