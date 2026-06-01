"""
AI Spec Generators — concrete implementations for AI providers.

This module contains generator classes that implement the SpecGeneratorProvider interface
for various AI services. Separated from providers_base.py to avoid circular imports.

IMPORTANT: AI ROLE BOUNDARIES
- All generators return structured data (ToolSpec objects), NOT file writes
- Generators fail gracefully when unavailable
- No autonomous file writes or command execution
- See ToolForge/docs/AI_ROLE_BOUNDARIES.md for full boundaries
"""

from __future__ import annotations

import os
import time
from typing import Any

from packages.core.spec_from_prompt import SpecGeneratorProvider
from packages.core.tool_spec import ToolSpec


class AzureOpenAISpecGenerator(SpecGeneratorProvider):
    """Generate ToolSpec using Azure OpenAI with structured output."""

    def __init__(
        self,
        endpoint: str,
        deployment: str,
        api_version: str = "2024-02-15-preview",
        model: str | None = None,
        max_retries: int = 3,
        timeout_seconds: int = 30,
        retry_backoff_seconds: int = 1,
    ) -> None:
        self._endpoint = endpoint
        self._deployment = deployment
        self._api_version = api_version
        self._model = model
        self._max_retries = max_retries
        self._timeout_seconds = timeout_seconds
        self._retry_backoff_seconds = retry_backoff_seconds

    def generate(self, prompt: str) -> ToolSpec:
        """Generate spec using Azure OpenAI with retry logic."""
        return self._generate_with_retry(self._generate_azure_openai, prompt)

    def _generate_with_retry(self, generator_func: Any, prompt: str) -> ToolSpec:
        """Generate spec with retry logic for transient errors."""
        import warnings

        last_error: Exception | None = None

        for attempt in range(self._max_retries):
            try:
                return generator_func(prompt)
            except Exception as e:
                last_error = e
                if self._is_non_retryable_error(e):
                    raise

                if attempt < self._max_retries - 1:
                    backoff = self._retry_backoff_seconds * (2**attempt)
                    warnings.warn(
                        f"Azure OpenAI generation attempt {attempt + 1} failed: {e}. "
                        f"Retrying in {backoff}s..."
                    )
                    time.sleep(backoff)
                else:
                    raise RuntimeError(
                        f"Azure OpenAI generation failed after {self._max_retries} attempts: {e}"
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

    def _generate_azure_openai(self, prompt: str) -> ToolSpec:
        """Generate spec using Azure OpenAI API."""
        try:
            import openai  # noqa: PLC0415
        except ImportError as e:
            raise ImportError("openai package required: pip install openai") from e

        api_key = os.environ.get("AZURE_OPENAI_API_KEY")
        if not api_key:
            raise ValueError(
                "AZURE_OPENAI_API_KEY environment variable not set or empty. "
                "Set it to use Azure OpenAI backend."
            )

        client = openai.AzureOpenAI(
            api_key=api_key,
            api_version=self._api_version,
            azure_endpoint=self._endpoint,
            timeout=self._timeout_seconds,
        )

        schema = ToolSpec.model_json_schema()
        system = (
            "You are ToolForge, a tool-spec generator. "
            "Given a natural-language description, produce a valid ToolSpec JSON object "
            "conforming exactly to the provided JSON Schema. "
            "Only output the JSON object — no markdown, no explanation."
        )

        response = client.chat.completions.create(
            model=self._deployment,
            messages=[
                {"role": "system", "content": system},
                {
                    "role": "user",
                    "content": (f"JSON Schema:\n{schema}\n\nTool description:\n{prompt}"),
                },
            ],
            response_format={"type": "json_object"},
        )

        data = response.choices[0].message.content
        if not data:
            raise ValueError("Azure OpenAI response did not contain JSON content")
        return ToolSpec.model_validate_json(data)


class DeepSeekSpecGeneratorWrapper(SpecGeneratorProvider):
    """Wrapper for DeepSeekProvider to conform to SpecGeneratorProvider interface."""

    def __init__(self, provider: Any) -> None:
        self._provider = provider

    def generate(self, prompt: str) -> ToolSpec:
        """Generate spec using DeepSeek provider."""
        spec_dict = self._provider.complete_json(prompt)
        try:
            return ToolSpec.model_validate(spec_dict)
        except Exception as e:
            raise ValueError(f"Failed to validate DeepSeek response as ToolSpec: {e}") from e
