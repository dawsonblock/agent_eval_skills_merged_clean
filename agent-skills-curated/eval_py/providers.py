"""
Provider abstraction for LLM-based judging.
Initial support: Anthropic Claude, OpenAI, LiteLLM stub.
"""
from typing import Any, Dict
from .exceptions import ProviderError


class JudgeProvider:
    def __init__(self, model: str):
        self.model = model

    def judge(self, prompt: str, **kwargs) -> Dict[str, Any]:
        raise NotImplementedError()


class AnthropicClaudeProvider(JudgeProvider):
    def judge(self, prompt: str, **kwargs) -> Dict[str, Any]:
        # TODO: Implement real API call
        raise ProviderError("Anthropic Claude API not implemented.")


class OpenAIProvider(JudgeProvider):
    def judge(self, prompt: str, **kwargs) -> Dict[str, Any]:
        # TODO: Implement real API call
        raise ProviderError("OpenAI API not implemented.")


class LiteLLMProvider(JudgeProvider):
    def judge(self, prompt: str, **kwargs) -> Dict[str, Any]:
        # Placeholder for local/Ollama/Grok
        raise ProviderError("LiteLLM adapter not implemented.")


def get_provider(provider_name: str, model: str) -> JudgeProvider:
    if provider_name == "anthropic":
        return AnthropicClaudeProvider(model)
    elif provider_name == "openai":
        return OpenAIProvider(model)
    elif provider_name == "litellm":
        return LiteLLMProvider(model)
    else:
        raise ProviderError(f"Unknown provider: {provider_name}")
