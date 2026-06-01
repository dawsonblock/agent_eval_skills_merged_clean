"""
AI Spec Generator — converts natural language prompts to ToolSpec YAML.

Supports multiple providers (OpenAI, Anthropic, Ollama, Azure OpenAI, DeepSeek) with
retry logic, timeout support, and fallback to rule-based generation.

IMPORTANT: AI ROLE BOUNDARIES
- This generator returns structured data (ToolSpec objects), NOT file writes
- All AI output must pass SpecValidator before being used
- Fallback to rule-based generation is mandatory on AI failure
- No autonomous file writes or command execution
- User approval is required before scaffolding AI-generated tools
- See ToolForge/docs/AI_ROLE_BOUNDARIES.md for full boundaries
"""

from __future__ import annotations

from packages.ai.generators import AzureOpenAISpecGenerator, DeepSeekSpecGeneratorWrapper
from packages.ai.providers.ollama_generator import OllamaSpecGenerator
from packages.ai.validation import validate_spec, ValidationResult
from packages.core.spec_from_prompt import (
    LLMSpecGenerator,
    RuleBasedSpecGenerator,
    SpecGeneratorProvider,
)
from packages.core.tool_spec import ToolSpec


class SpecValidationError(Exception):
    """Exception raised when AI-generated spec fails validation."""

    def __init__(self, validation_result: ValidationResult) -> None:
        self.validation_result = validation_result
        super().__init__(self._format_errors())

    def _format_errors(self) -> str:
        """Format validation errors into a readable message."""
        error_messages = [f"{e.field}: {e.message}" for e in self.validation_result.errors]
        return "Generated spec failed validation:\n" + "\n".join(error_messages)


class AISpecGenerator:
    """
    Unified facade for AI-powered ToolSpec generation.

    Supports multiple providers with automatic retry, validation, and fallback.
    """

    def __init__(
        self,
        provider: str = "rule_based",
        backend: str = "openai",
        model: str | None = None,
        max_retries: int = 3,
        timeout_seconds: int = 30,
        retry_backoff_seconds: int = 1,
        fallback_to_rule_based: bool = True,
        ollama_base_url: str = "http://localhost:11434",
        azure_openai_endpoint: str | None = None,
        azure_openai_deployment: str | None = None,
        azure_openai_api_version: str = "2024-02-15-preview",
    ) -> None:
        """
        Initialize the AI Spec Generator.

        Args:
            provider: AI provider ("rule_based", "openai", "anthropic", "ollama", "azure_openai")
            backend: LLM backend for "llm" provider ("openai", "anthropic")
            model: Override default model for the chosen provider
            max_retries: Number of retry attempts for transient errors (default: 3)
            timeout_seconds: Timeout in seconds for API calls (default: 30)
            retry_backoff_seconds: Base backoff in seconds for retry logic (default: 1)
            fallback_to_rule_based: Automatically fallback to rule-based on failure (default: True)
            ollama_base_url: Base URL for Ollama API (default: http://localhost:11434)
            azure_openai_endpoint: Azure OpenAI endpoint URL
            azure_openai_deployment: Azure OpenAI deployment name
            azure_openai_api_version: Azure OpenAI API version (default: 2024-02-15-preview)

        Raises:
            ValueError: If required parameters are missing for the chosen provider
        """
        # Validate azure_openai provider requirements
        if provider == "azure_openai":
            if not azure_openai_deployment:
                raise ValueError("azure_openai_deployment is required for azure_openai provider")
            if not azure_openai_endpoint:
                raise ValueError("azure_openai_endpoint is required for azure_openai provider")

        self._provider = provider
        self._backend = backend
        self._model = model
        self._max_retries = max_retries
        self._timeout_seconds = timeout_seconds
        self._retry_backoff_seconds = retry_backoff_seconds
        self._fallback_to_rule_based = fallback_to_rule_based
        self._ollama_base_url = ollama_base_url
        self._azure_openai_endpoint = azure_openai_endpoint
        self._azure_openai_deployment = azure_openai_deployment
        self._azure_openai_api_version = azure_openai_api_version

    def generate(self, prompt: str) -> ToolSpec:
        """
        Generate a ToolSpec from a natural-language prompt.

        Args:
            prompt: Natural-language description of the tool

        Returns:
            ToolSpec object

        Raises:
            RuntimeError: If generation fails and fallback is disabled
        """
        try:
            spec = self._generate_with_provider(prompt)
            # Validate the generated spec
            validation_result = validate_spec(spec)
            if validation_result.has_errors():
                raise SpecValidationError(validation_result)
            return spec
        except SpecValidationError as e:
            if self._fallback_to_rule_based and self._provider != "rule_based":
                import warnings

                warnings.warn(
                    f"AI generation with provider '{self._provider}' failed validation: {e}. "
                    "Falling back to rule-based generation."
                )
                return self._generate_rule_based(prompt)
            raise
        except Exception as e:
            if self._fallback_to_rule_based and self._provider != "rule_based":
                import warnings

                warnings.warn(
                    f"AI generation with provider '{self._provider}' failed: {e}. "
                    "Falling back to rule-based generation."
                )
                return self._generate_rule_based(prompt)
            raise

    def _generate_with_provider(self, prompt: str) -> ToolSpec:
        """Generate spec using the configured provider."""
        generator = self._create_generator()
        return generator.generate(prompt)

    def _create_generator(self) -> SpecGeneratorProvider:
        """Create the appropriate generator based on provider configuration."""
        if self._provider == "rule_based":
            return RuleBasedSpecGenerator()

        if self._provider in ("openai", "anthropic"):
            return LLMSpecGenerator(
                backend=self._backend,
                model=self._model,
                max_retries=self._max_retries,
                timeout_seconds=self._timeout_seconds,
                retry_backoff_seconds=self._retry_backoff_seconds,
            )

        if self._provider == "ollama":
            return OllamaSpecGenerator(
                model=self._model or "llama3",
                base_url=self._ollama_base_url,
                max_retries=self._max_retries,
                timeout_seconds=self._timeout_seconds,
                retry_backoff_seconds=self._retry_backoff_seconds,
            )

        if self._provider == "azure_openai":
            # Azure OpenAI uses the OpenAI client with custom configuration
            return self._create_azure_openai_generator()

        if self._provider == "deepseek":
            return self._create_deepseek_generator()

        raise ValueError(f"Unknown provider: {self._provider}")

    def _create_azure_openai_generator(self) -> SpecGeneratorProvider:
        """Create Azure OpenAI generator."""
        import importlib.util

        if not importlib.util.find_spec("openai"):
            raise ImportError("openai package required: pip install openai")

        if not self._azure_openai_endpoint:
            raise ValueError("azure_openai_endpoint required for azure_openai provider")

        if not self._azure_openai_deployment:
            raise ValueError("azure_openai_deployment required for azure_openai provider")

        # Azure OpenAI uses the standard OpenAI client with custom endpoint
        # We'll create a custom generator class for this
        return AzureOpenAISpecGenerator(
            endpoint=self._azure_openai_endpoint,
            deployment=self._azure_openai_deployment,
            api_version=self._azure_openai_api_version,
            model=self._model,
            max_retries=self._max_retries,
            timeout_seconds=self._timeout_seconds,
            retry_backoff_seconds=self._retry_backoff_seconds,
        )

    def _create_deepseek_generator(self) -> SpecGeneratorProvider:
        """Create DeepSeek generator."""
        import importlib.util

        if not importlib.util.find_spec("openai"):
            raise ImportError("openai package required: pip install openai")

        # DeepSeek uses OpenAI-compatible API
        from packages.ai.providers.deepseek_provider import DeepSeekProvider

        provider = DeepSeekProvider(
            model=self._model or "deepseek-chat",
            api_key=None,  # Uses DEEPSEEK_API_KEY env var
            max_retries=self._max_retries,
            timeout_seconds=self._timeout_seconds,
        )

        # Create a wrapper that converts provider output to ToolSpec
        return DeepSeekSpecGeneratorWrapper(provider)

    def _generate_rule_based(self, prompt: str) -> ToolSpec:
        """Generate spec using rule-based generator as fallback."""
        generator = RuleBasedSpecGenerator()
        return generator.generate(prompt)
