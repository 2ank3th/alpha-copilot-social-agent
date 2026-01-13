"""LLM client for the agent using google-genai package with native function calling."""

import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field

from google import genai
from google.genai import types
from google.genai.errors import ServerError

from .config import Config
from .retry import retry_with_backoff

logger = logging.getLogger(__name__)


@dataclass
class LLMResponse:
    """Structured response from LLM."""
    reasoning: str
    tool_call: Optional[Dict[str, Any]] = None
    is_done: bool = False
    grounding_sources: Optional[List[str]] = None
    # Store the raw response for conversation history (preserves thought signatures)
    raw_content: Optional[Any] = field(default=None, repr=False)


class LLMClient:
    """Client for interacting with Gemini LLM with native function calling.

    Uses the google-genai package with native function calling API.
    This approach is more reliable than JSON-in-prompt parsing and
    properly handles Gemini 3's thought signatures.
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
        contents: List[Any],
        tools: List[Dict[str, Any]]
    ) -> LLMResponse:
        """
        Generate a response using native Gemini function calling.

        Args:
            contents: Conversation history (Gemini Content objects or dicts)
            tools: Available tool schemas

        Returns:
            LLMResponse with reasoning and optional tool call

        Raises:
            Exception: If LLM generation fails
        """
        # Convert tool schemas to Gemini function declarations
        function_declarations = self._convert_to_function_declarations(tools)

        # Build tools list - function calling tool only
        # NOTE: Gemini API does not support combining function calling with
        # Google Search grounding in the same request. When using function
        # calling, grounding must be disabled.
        gemini_tools = [types.Tool(function_declarations=function_declarations)]

        # Configure generation with tools
        config = types.GenerateContentConfig(
            temperature=0.7,
            max_output_tokens=2048,
            tools=gemini_tools,
        )

        def _do_generate():
            """Inner function for retry wrapper."""
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=contents,
                config=config,
            )

            # Parse the response to extract function call or text
            parsed = self._parse_native_response(response)

            # Extract grounding sources if available
            grounding_sources = self._extract_grounding_sources(response)
            if grounding_sources:
                logger.info(f"Grounding sources used: {len(grounding_sources)}")
            parsed.grounding_sources = grounding_sources

            return parsed

        # Use retry utility for transient server errors
        return retry_with_backoff(
            func=_do_generate,
            retryable_exceptions=ServerError,
            operation_name="Gemini LLM generation",
        )

    def _convert_to_function_declarations(
        self,
        tools: List[Dict[str, Any]]
    ) -> List[types.FunctionDeclaration]:
        """Convert tool schemas to Gemini FunctionDeclaration format."""
        declarations = []

        for tool in tools:
            # Extract parameters schema
            params = tool.get("parameters", {})

            declaration = types.FunctionDeclaration(
                name=tool["name"],
                description=tool["description"],
                parameters=params if params else None,
            )
            declarations.append(declaration)

        return declarations

    def _parse_native_response(self, response) -> LLMResponse:
        """Parse native Gemini response to extract function call or text."""
        reasoning = ""
        tool_call = None
        raw_content = None

        try:
            # Get the first candidate
            if not response.candidates:
                return LLMResponse(reasoning="No response generated", raw_content=None)

            candidate = response.candidates[0]
            raw_content = candidate.content

            # Iterate through parts to find function calls and text
            if candidate.content and candidate.content.parts:
                for part in candidate.content.parts:
                    # Check for function call
                    if hasattr(part, 'function_call') and part.function_call:
                        fc = part.function_call
                        tool_call = {
                            "name": fc.name,
                            "arguments": dict(fc.args) if fc.args else {}
                        }
                        logger.info(f"Function call detected: {fc.name}")

                    # Check for text content
                    if hasattr(part, 'text') and part.text:
                        reasoning += part.text

            # If no text reasoning, use a default
            if not reasoning:
                if tool_call:
                    reasoning = f"Calling {tool_call['name']}"
                else:
                    reasoning = "Processing..."

        except Exception as e:
            logger.error(f"Error parsing response: {e}")
            # Try to get text as fallback
            try:
                reasoning = response.text if hasattr(response, 'text') else str(response)
            except Exception:
                reasoning = "Error parsing response"

        return LLMResponse(
            reasoning=reasoning,
            tool_call=tool_call,
            is_done=(tool_call["name"] == "done" if tool_call else False),
            raw_content=raw_content,
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
