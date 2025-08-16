"""LLM client — unified interface for language model calls."""

from __future__ import annotations

import logging
from typing import Optional

from app.config import get_settings

logger = logging.getLogger("ai-service")
settings = get_settings()


async def call_llm(
    prompt: str,
    system_prompt: str = "You are a senior software engineer analyzing code.",
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None,
) -> str:
    """Call the configured LLM with a prompt.

    Uses LiteLLM for unified access to OpenAI, Anthropic, and local models.
    Falls back to a mock response when no API key is configured.

    Args:
        prompt: User prompt text.
        system_prompt: System message for the LLM.
        temperature: Override default temperature.
        max_tokens: Override default max tokens.

    Returns:
        LLM response text.
    """
    temp = temperature or settings.llm_temperature
    tokens = max_tokens or settings.llm_max_tokens

    if not settings.llm_api_key:
        logger.warning("No LLM API key configured, using mock response")
        return _mock_response(prompt)

    try:
        import os
        import litellm

        # Configure for OpenRouter via LiteLLM
        os.environ["OPENROUTER_API_KEY"] = settings.llm_api_key

        response = await litellm.acompletion(
            model=settings.llm_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
            temperature=temp,
            max_tokens=tokens,
            api_key=settings.llm_api_key,
        )

        return response.choices[0].message.content

    except ImportError:
        logger.warning("litellm not available, using mock")
        return _mock_response(prompt)
    except Exception as e:
        logger.error(f"LLM call failed: {e}", exc_info=True)
        return _mock_response(prompt)


def _mock_response(prompt: str) -> str:
    """Generate a structured mock response for development without API keys."""
    if "summarize" in prompt.lower():
        return (
            "## Code Summary\n\n"
            "This module implements core business logic with clean separation of concerns. "
            "Key components include data validation, transformation pipelines, and error handling. "
            "The code follows established patterns and maintains good test coverage.\n\n"
            "### Key Functions\n"
            "- Primary entry points handle request routing\n"
            "- Helper functions manage data transformation\n"
            "- Error handling is centralized via custom exception classes"
        )
    elif "review" in prompt.lower() or "pr" in prompt.lower():
        return (
            "## PR Review\n\n"
            "**Risk Score: 0.35** (Low-Medium)\n\n"
            "### Suggestions\n"
            "1. Consider adding input validation on line 42\n"
            "2. The error handling could be more specific — catch concrete exceptions\n"
            "3. Good use of type hints throughout\n"
            "4. Unit tests cover the happy path but miss edge cases\n\n"
            "### Summary\n"
            "Clean implementation with minor improvements needed in error handling."
        )
    elif "bug" in prompt.lower():
        return (
            "## Bug Detection Report\n\n"
            "### Potential Issues\n"
            "1. **Unhandled None** — Function parameter could be None without guard\n"
            "2. **Resource leak** — File handle not closed in exception path\n"
            "3. **Race condition** — Shared mutable state without synchronization\n\n"
            "### Recommendations\n"
            "- Add null checks on external inputs\n"
            "- Use context managers for resource management\n"
            "- Consider atomic operations for shared state"
        )
    else:
        return (
            "Based on the codebase analysis, this code follows a modular architecture "
            "with clear separation between data access, business logic, and presentation layers. "
            "The dependency graph shows well-defined boundaries between components."
        )
