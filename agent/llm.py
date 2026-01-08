"""LLM client for the agent using google-genai package."""

import json
import logging
import re
import time
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

from google import genai
from google.genai import types
from google.genai.errors import ServerError

from .config import Config

logger = logging.getLogger(__name__)

# Retry configuration
MAX_RETRIES = 3
RETRY_DELAY_SECONDS = 2.0
RETRY_BACKOFF_MULTIPLIER = 2.0


@dataclass
class LLMResponse:
    """Structured response from LLM."""
    reasoning: str
    tool_call: Optional[Dict[str, Any]] = None
    is_done: bool = False
    grounding_sources: Optional[List[str]] = None


class LLMClient:
    """Client for interacting with Gemini LLM with Google Search grounding.

    Uses the google-genai package (not the deprecated google-generativeai).
    Raises exceptions on failure - no silent fallbacks.
    """

    def __init__(self, enable_grounding: bool = True):
        """Initialize the LLM client.

        Args:
            enable_grounding: Enable Google Search grounding for web research

        Raises:
            ValueError: If GEMINI_API_KEY is not configured
            Exception: If client initialization fails
        """
        if not Config.GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY not configured")

        self.client = genai.Client(api_key=Config.GEMINI_API_KEY)
        self.model_name = Config.LLM_MODEL
        self.enable_grounding = enable_grounding

        # Configure grounding tool if enabled
        if enable_grounding:
            self.grounding_tool = types.Tool(
                google_search=types.GoogleSearch()
            )
            logger.info("LLM initialized with Google Search grounding enabled")
        else:
            self.grounding_tool = None
            logger.info("LLM initialized without grounding")

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

        Raises:
            Exception: If LLM generation fails
        """
        # Build prompt with tool instructions
        prompt = self._build_prompt_with_tools(messages, tools)

        # Configure generation
        config = types.GenerateContentConfig(
            temperature=0.7,
            max_output_tokens=1024,
        )

        # Retry loop for transient errors
        last_error = None
        delay = RETRY_DELAY_SECONDS

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                # Generate response using new API
                response = self.client.models.generate_content(
                    model=self.model_name,
                    contents=prompt,
                    config=config,
                )

                # Extract text from response
                response_text = response.text if hasattr(response, 'text') and response.text else str(response)

                # Ensure response_text is a string
                if not isinstance(response_text, str):
                    response_text = str(response_text)

                # Extract grounding sources if available
                grounding_sources = self._extract_grounding_sources(response)
                if grounding_sources:
                    logger.info(f"Grounding sources used: {len(grounding_sources)}")

                parsed = self._parse_response(response_text)
                parsed.grounding_sources = grounding_sources
                return parsed

            except ServerError as e:
                # Retry on 500/503 server errors
                last_error = e
                if attempt < MAX_RETRIES:
                    logger.warning(
                        f"Gemini server error (attempt {attempt}/{MAX_RETRIES}): {e}. "
                        f"Retrying in {delay:.1f}s..."
                    )
                    time.sleep(delay)
                    delay *= RETRY_BACKOFF_MULTIPLIER
                else:
                    logger.error(f"Gemini server error after {MAX_RETRIES} attempts: {e}")
                    raise

            except Exception as e:
                # Don't retry on other errors (auth, validation, etc.)
                logger.exception("LLM generation failed (non-retryable)")
                raise

        # Should not reach here, but just in case
        if last_error:
            raise last_error

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

    def _extract_grounding_sources(self, response) -> Optional[List[str]]:
        """Extract grounding sources from response metadata."""
        sources = []
        try:
            # Check for grounding metadata in candidates
            if hasattr(response, 'candidates') and response.candidates:
                for candidate in response.candidates:
                    if hasattr(candidate, 'grounding_metadata') and candidate.grounding_metadata:
                        metadata = candidate.grounding_metadata
                        # Extract from grounding_chunks
                        if hasattr(metadata, 'grounding_chunks') and metadata.grounding_chunks:
                            for chunk in metadata.grounding_chunks:
                                if hasattr(chunk, 'web') and chunk.web:
                                    uri = getattr(chunk.web, 'uri', None)
                                    title = getattr(chunk.web, 'title', None)
                                    if uri:
                                        sources.append(f"{title}: {uri}" if title else uri)
                        # Log search queries used
                        if hasattr(metadata, 'web_search_queries') and metadata.web_search_queries:
                            logger.debug(f"Search queries: {metadata.web_search_queries}")
        except Exception as e:
            # Log but don't fail - grounding metadata extraction is non-critical
            logger.debug(f"Could not extract grounding sources: {e}")

        return sources if sources else None
