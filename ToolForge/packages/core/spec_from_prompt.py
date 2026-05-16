"""
Spec-from-prompt — generate a ToolSpec from a natural-language description.

Providers:
  RuleBasedSpecGenerator — keyword/heuristic extraction, no LLM required (DEFAULT)
  LLMSpecGenerator       — structured output via OpenAI / Anthropic
"""
from __future__ import annotations

import re
from abc import ABC, abstractmethod
from datetime import datetime, timezone

from packages.core.tool_spec import (
    EvalCase,
    EvalCriterion,
    EvalCriterionType,
    EvalSpec,
    MCPSpec,
    ParameterSpec,
    PrivacyLevel,
    SecuritySpec,
    SkillSpec,
    ToolLanguage,
    ToolSpec,
)


# ---------------------------------------------------------------------------
# Abstract provider
# ---------------------------------------------------------------------------


class SpecGeneratorProvider(ABC):
    @abstractmethod
    def generate(self, prompt: str) -> ToolSpec:
        """Generate a ToolSpec from a natural-language *prompt*."""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_SLUG_RE = re.compile(r"[^a-z0-9]+")


def _to_slug(text: str) -> str:
    return _SLUG_RE.sub("-", text.lower()).strip("-")


_PYTHON_KEYWORDS = {"python", "py", ".py", "script", "pandas", "numpy", "csv"}
_TS_KEYWORDS = {"typescript", "ts", "node", "javascript", "js", "npm", "react"}
_FILE_KEYWORDS = {"file", "csv", "json", "pdf", "excel", "xlsx", "read", "write", "parse"}
_WEB_KEYWORDS = {"fetch", "http", "url", "scrape", "crawl", "request", "api", "web"}
_CODE_KEYWORDS = {"code", "lint", "format", "compile", "test", "run", "execute"}


def _detect_language(prompt: str) -> ToolLanguage:
    lower = prompt.lower()
    ts_hits = sum(1 for kw in _TS_KEYWORDS if kw in lower)
    py_hits = sum(1 for kw in _PYTHON_KEYWORDS if kw in lower)
    return ToolLanguage.TYPESCRIPT if ts_hits > py_hits else ToolLanguage.PYTHON


def _extract_name(prompt: str) -> str:
    """Best-effort name extraction from prompt."""
    # "Create a tool that …" → use first noun phrase after "tool"
    m = re.search(r'\btool\s+(?:that|to|for|which)\s+(.+?)(?:[.,!?]|$)', prompt, re.IGNORECASE)
    if m:
        phrase = m.group(1).strip()
        # Capitalise words, limit to 5 words
        words = phrase.split()[:5]
        return " ".join(w.capitalize() for w in words)

    # Try "named …" or "called …"
    m2 = re.search(r'(?:named|called)\s+"?([A-Za-z0-9 _-]+)"?', prompt, re.IGNORECASE)
    if m2:
        return m2.group(1).strip().title()

    # Fall back to first 4 words
    words = re.sub(r'[^a-zA-Z0-9 ]', '', prompt).split()[:4]
    return " ".join(w.capitalize() for w in words) or "Generated Tool"


def _infer_category(prompt: str) -> str:
    lower = prompt.lower()
    if any(kw in lower for kw in _FILE_KEYWORDS):
        return "file-processing"
    if any(kw in lower for kw in _WEB_KEYWORDS):
        return "web-and-automation"
    if any(kw in lower for kw in _CODE_KEYWORDS):
        return "coding-agents-and-ides"
    return "general"


def _extract_tags(prompt: str) -> list[str]:
    tags: list[str] = []
    lower = prompt.lower()
    candidates = [
        "csv", "json", "pdf", "excel", "yaml", "xml",
        "web", "api", "http", "file", "text", "image",
        "python", "typescript", "bash", "sql",
        "lint", "format", "validate", "convert", "parse", "extract",
    ]
    for c in candidates:
        if c in lower:
            tags.append(c)
    return tags[:8]  # cap


# ---------------------------------------------------------------------------
# Rule-based provider
# ---------------------------------------------------------------------------


class RuleBasedSpecGenerator(SpecGeneratorProvider):
    """Heuristic spec generator — no external calls required."""

    def generate(self, prompt: str) -> ToolSpec:
        name = _extract_name(prompt)
        slug = _to_slug(name)
        language = _detect_language(prompt)
        category = _infer_category(prompt)
        tags = _extract_tags(prompt)

        # Generate a minimal ParameterSpec from keywords
        params: list[ParameterSpec] = [
            ParameterSpec(
                name="input",
                type="string",
                description="Primary input for the tool",
                required=True,
            )
        ]

        # Infer if tool needs filesystem/network access from prompt
        requires_filesystem = any(kw in prompt.lower() for kw in _FILE_KEYWORDS)
        requires_network = any(kw in prompt.lower() for kw in _WEB_KEYWORDS)

        # Build eval cases with 3 defaults: success, invalid input, safety boundary
        eval_cases = [
            EvalCase(
                id="case-01-success",
                description="Basic success case",
                inputs={"input": "test_data"},
                expected_output=None,
                tags=["smoke"],
            ),
            EvalCase(
                id="case-02-invalid-input",
                description="Invalid or empty input",
                inputs={"input": ""},
                expected_output=None,
                tags=["edge-case"],
            ),
        ]
        
        # Add safety-boundary case if filesystem access is involved
        if requires_filesystem:
            eval_cases.append(
                EvalCase(
                    id="case-03-safety-boundary",
                    description="Path traversal attempt (should be blocked)",
                    inputs={"input": "../../../etc/passwd"},
                    expected_output=None,
                    tags=["safety"],
                )
            )

        # Eval spec with criteria
        eval_spec = EvalSpec(
            enabled=True,
            baseline_pass_rate=0.8,
            criteria=[
                EvalCriterion(
                    name="no_error",
                    type=EvalCriterionType.NO_ERROR,
                    description="Tool runs without errors",
                    weight=1.0,
                )
            ],
            cases=eval_cases,
        )

        # Security spec with inferred permissions
        security_spec = SecuritySpec(
            requires_filesystem=requires_filesystem,
            requires_network=requires_network,
            required_capabilities=[],
            allowed_read_paths=["./examples/**", "./inputs/**"] if requires_filesystem else [],
            allowed_write_paths=["./outputs/**"] if requires_filesystem else [],
            allowed_extensions=[".csv", ".json", ".txt"] if requires_filesystem else [],
            max_file_size_mb=50,
            privacy_level=PrivacyLevel.INTERNAL,
        )

        return ToolSpec(
            name=name,
            slug=slug,
            version="0.1.0",
            description=prompt[:120].rstrip(".") + ".",
            long_description=prompt,
            tags=tags,
            language=language,
            entry_point="tool.py" if language == ToolLanguage.PYTHON else "index.ts",
            parameters=params,
            security=security_spec,
            mcp=MCPSpec(enabled=True),
            skill=SkillSpec(enabled=True, category=category),
            eval=eval_spec,
            source_prompt=prompt,
            created_at=datetime.now(timezone.utc).isoformat(),
        )


# ---------------------------------------------------------------------------
# LLM provider (optional — requires openai or anthropic extra)
# ---------------------------------------------------------------------------


class LLMSpecGenerator(SpecGeneratorProvider):
    """
    Generate a ToolSpec via an LLM with structured output.

    Requires the ``openai`` package and ``OPENAI_API_KEY`` env var,
    or the ``anthropic`` package and ``ANTHROPIC_API_KEY`` env var.
    """

    def __init__(self, backend: str = "openai", model: str | None = None) -> None:
        self._backend = backend
        self._model = model

    def generate(self, prompt: str) -> ToolSpec:
        if self._backend == "openai":
            return self._generate_openai(prompt)
        if self._backend == "anthropic":
            return self._generate_anthropic(prompt)
        raise ValueError(f"Unknown LLM backend: {self._backend!r}")

    def _generate_openai(self, prompt: str) -> ToolSpec:
        try:
            import openai  # noqa: PLC0415
        except ImportError as e:
            raise ImportError("openai package required: pip install openai") from e

        import os

        client = openai.OpenAI(api_key=os.environ["OPENAI_API_KEY"])
        schema = ToolSpec.model_json_schema()
        system = (
            "You are ToolForge, a tool-spec generator. "
            "Given a natural-language description, produce a valid ToolSpec JSON object "
            "conforming exactly to the provided JSON Schema. "
            "Only output the JSON object — no markdown, no explanation."
        )
        response = client.chat.completions.create(
            model=self._model or "gpt-4o-mini",
            messages=[
                {"role": "system", "content": system},
                {
                    "role": "user",
                    "content": (
                        f"JSON Schema:\n{schema}\n\n"
                        f"Tool description:\n{prompt}"
                    ),
                },
            ],
            response_format={"type": "json_object"},
        )
        data = response.choices[0].message.content
        return ToolSpec.model_validate_json(data)

    def _generate_anthropic(self, prompt: str) -> ToolSpec:
        try:
            import anthropic  # noqa: PLC0415
        except ImportError as e:
            raise ImportError("anthropic package required: pip install anthropic") from e

        import json
        import os

        client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
        schema = ToolSpec.model_json_schema()
        message = client.messages.create(
            model=self._model or "claude-3-haiku-20240307",
            max_tokens=4096,
            messages=[
                {
                    "role": "user",
                    "content": (
                        "You are ToolForge. Given this JSON Schema and description, "
                        "return ONLY a valid JSON object conforming to the schema.\n\n"
                        f"Schema:\n{json.dumps(schema)}\n\n"
                        f"Description:\n{prompt}"
                    ),
                }
            ],
        )
        return ToolSpec.model_validate_json(message.content[0].text)


# ---------------------------------------------------------------------------
# Public factory
# ---------------------------------------------------------------------------


def generate_spec_from_prompt(
    prompt: str,
    provider: str = "rule_based",
    backend: str = "openai",
    model: str | None = None,
) -> ToolSpec:
    """
    Generate a ToolSpec from *prompt* using the given *provider*.

    Args:
        prompt:   Natural-language description of the tool.
        provider: "rule_based" (default) or "llm".
        backend:  LLM backend when provider="llm" — "openai" or "anthropic".
        model:    Override the default model for the chosen backend.
    """
    if provider == "llm":
        gen: SpecGeneratorProvider = LLMSpecGenerator(backend=backend, model=model)
    else:
        gen = RuleBasedSpecGenerator()
    return gen.generate(prompt)
