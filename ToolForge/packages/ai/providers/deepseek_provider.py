"""
DeepSeek provider for AI spec generation.

DeepSeek uses an OpenAI-compatible API endpoint.
"""

from __future__ import annotations

import json
import os
from typing import Any

from packages.ai.providers_base import AIProvider
from packages.core.tool_spec import ToolSpec


class DeepSeekProvider(AIProvider):
    """
    DeepSeek provider using OpenAI-compatible API.

    DeepSeek uses an OpenAI-compatible API endpoint.
    """

    def __init__(
        self,
        model: str = "deepseek-chat",
        api_key: str | None = None,
        base_url: str = "https://api.deepseek.com",
        max_retries: int = 3,
        timeout_seconds: int = 30,
        retry_backoff_seconds: int = 1,
    ) -> None:
        self._model = model
        self._api_key = api_key
        self._base_url = base_url
        self._max_retries = max_retries
        self._timeout_seconds = timeout_seconds
        self._retry_backoff_seconds = retry_backoff_seconds

    def complete_json(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        timeout: int = 30,
    ) -> dict[str, Any]:
        """
        Complete a prompt using DeepSeek API.

        Args:
            prompt: The user prompt
            system_prompt: Optional system prompt
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            timeout: Request timeout in seconds

        Returns:
            The ToolSpec as a dict
        """
        return self._complete_with_retry(
            self._complete_impl, prompt, system_prompt, temperature, max_tokens
        )

    def _complete_with_retry(
        self,
        complete_func: Any,
        prompt: str,
        system_prompt: str | None,
        temperature: float,
        max_tokens: int,
    ) -> dict[str, Any]:
        """Complete with retry logic for transient errors."""
        import time
        import warnings

        last_error: Exception | None = None

        for attempt in range(self._max_retries):
            try:
                return complete_func(prompt, system_prompt, temperature, max_tokens)
            except Exception as e:
                last_error = e
                if self._is_non_retryable_error(e):
                    raise

                if attempt < self._max_retries - 1:
                    backoff = self._retry_backoff_seconds * (2**attempt)
                    warnings.warn(
                        f"DeepSeek generation attempt {attempt + 1} failed: {e}. "
                        f"Retrying in {backoff}s..."
                    )
                    time.sleep(backoff)
                else:
                    raise RuntimeError(
                        f"DeepSeek generation failed after {self._max_retries} attempts: {e}"
                    ) from last_error

        raise RuntimeError("Unexpected error in retry logic") from last_error

    def _is_non_retryable_error(self, error: Exception) -> bool:
        """Check if error should not be retried."""
        error_str = str(error).lower()
        # Check non-retryable patterns first - these should fail immediately
        non_retryable_patterns = [
            "authentication",
            "api key",
            "unauthorized",
            "malformed",
        ]
        if any(pattern in error_str for pattern in non_retryable_patterns):
            return True
        # If error doesn't match non-retryable patterns, allow retry by default
        return False

    def _complete_impl(
        self,
        prompt: str,
        system_prompt: str | None,
        temperature: float,
        max_tokens: int,
    ) -> dict[str, Any]:
        """Implementation of DeepSeek API call."""
        try:
            import openai  # noqa: PLC0415
        except ImportError as e:
            raise ImportError("openai package required: pip install openai") from e

        api_key = self._api_key or os.environ.get("DEEPSEEK_API_KEY")
        if not api_key:
            raise ValueError(
                "DeepSeek API key not set. Set DEEPSEEK_API_KEY environment variable "
                "or pass api_key parameter."
            )

        client = openai.OpenAI(api_key=api_key, base_url=self._base_url)

        schema = ToolSpec.model_json_schema()
        system = system_prompt or (
            "You are ToolForge, a tool-spec generator. "
            "Given a natural-language description, produce a valid ToolSpec JSON object "
            "conforming exactly to the provided JSON Schema. "
            "Only output the JSON object — no markdown, no explanation."
        )

        response = client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": system},
                {
                    "role": "user",
                    "content": f"JSON Schema:\n{schema}\n\nTool description:\n{prompt}",
                },
            ],
            temperature=temperature,
            max_tokens=max_tokens,
            response_format={"type": "json_object"},
            timeout=self._timeout_seconds,
        )

        content = response.choices[0].message.content
        if not content:
            raise ValueError("DeepSeek returned empty response")

        return json.loads(content)

    def is_available(self) -> bool:
        """
        Check if DeepSeek is available.

        Returns:
            True if API key is set, False otherwise
        """
        try:
            api_key = self._api_key or os.environ.get("DEEPSEEK_API_KEY")
            return api_key is not None and len(api_key) > 0
        except Exception:
            return False
