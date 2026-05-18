"""AI provider implementations for spec generation."""
from __future__ import annotations

from packages.ai.providers.ollama_generator import OllamaSpecGenerator
from packages.ai.providers.deepseek_provider import DeepSeekProvider

__all__ = ["OllamaSpecGenerator", "DeepSeekProvider"]
