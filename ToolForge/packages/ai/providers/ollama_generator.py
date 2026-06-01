"""
Ollama provider for local model-based spec generation.

Uses the Ollama API to generate ToolSpec objects using local models.
"""

from __future__ import annotations

import time
from typing import Any

from packages.core.spec_from_prompt import SpecGeneratorProvider
from packages.core.tool_spec import ToolSpec


class OllamaSpecGenerator(SpecGeneratorProvider):
    """
    Generate a ToolSpec via Ollama with structured output.

    Requires Ollama to be running locally with a compatible model.
    """

    def __init__(
        self,
        model: str = "llama3",
        base_url: str = "http://localhost:11434",
        max_retries: int = 3,
        timeout_seconds: int = 30,
        retry_backoff_seconds: int = 1,
    ) -> None:
        self._model = model
        self._base_url = base_url
        self._max_retries = max_retries
        self._timeout_seconds = timeout_seconds
        self._retry_backoff_seconds = retry_backoff_seconds

    def generate(self, prompt: str) -> ToolSpec:
        """Generate spec using Ollama with retry logic."""
        return self._generate_with_retry(self._generate_ollama, prompt)

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
                        f"Ollama generation attempt {attempt + 1} failed: {e}. "
                        f"Retrying in {backoff}s..."
                    )
                    time.sleep(backoff)
                else:
                    raise RuntimeError(
                        f"Ollama generation failed after {self._max_retries} attempts: {e}"
                    ) from last_error

        raise RuntimeError("Unexpected error in retry logic") from last_error

    def _is_non_retryable_error(self, error: Exception) -> bool:
        """Check if error should not be retried."""
        error_str = str(error).lower()
        # Check non-retryable patterns first - these should fail immediately
        non_retryable_patterns = [
            "model not found",
            "malformed",
        ]
        if any(pattern in error_str for pattern in non_retryable_patterns):
            return True
        # If error doesn't match non-retryable patterns, allow retry by default
        return False

    def _generate_ollama(self, prompt: str) -> ToolSpec:
        """Generate spec using Ollama API."""
        try:
            import requests  # noqa: PLC0415
        except ImportError as e:
            raise ImportError("requests package required: pip install requests") from e

        schema = ToolSpec.model_json_schema()
        system = (
            "You are ToolForge, a tool-spec generator. "
            "Given a natural-language description, produce a valid ToolSpec JSON object "
            "conforming exactly to the provided JSON Schema. "
            "Only output the JSON object — no markdown, no explanation."
        )

        user_message = f"JSON Schema:\n{schema}\n\nTool description:\n{prompt}"

        response = requests.post(
            f"{self._base_url}/api/generate",
            json={
                "model": self._model,
                "prompt": user_message,
                "system": system,
                "stream": False,
                "format": "json",
            },
            timeout=self._timeout_seconds,
        )

        response.raise_for_status()
        data = response.json()

        # Handle different Ollama response structures
        if "response" in data:
            # Standard Ollama response with 'response' field
            response_data = data["response"]
            # The response field may be a JSON string or a dict
            if isinstance(response_data, str):
                return ToolSpec.model_validate_json(response_data)
            json_data = response_data
        elif isinstance(data, dict) and all(k in data for k in ["name", "slug", "version"]):
            # Direct ToolSpec structure
            json_data = data
        else:
            # Try using the entire response as JSON
            json_data = data

        try:
            return ToolSpec.model_validate(json_data)
        except Exception as e:
            raise ValueError(
                f"Failed to parse Ollama response as ToolSpec. "
                f"Response keys: {list(data.keys())}. Error: {e}"
            ) from e
