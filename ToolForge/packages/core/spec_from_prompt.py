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

    # Keyword-based name/slug override rules: (keywords_any, slug, human_name)
    _SLUG_OVERRIDES: list[tuple[set[str], str, str]] = [
        ({"csv", "comma-separated"}, "csv-cleaner", "CSV Cleaner"),
        ({"json", "schema", "validate"}, "json-schema-validator", "JSON Schema Validator"),
        ({"hash", "sha256", "checksum"}, "local-file-hasher", "Local File Hasher"),
        ({"fetch", "scrape", "crawl"}, "web-fetcher", "Web Fetcher"),
    ]

    def generate(self, prompt: str) -> ToolSpec:
        lower_prompt = prompt.lower()

        # Apply keyword-based overrides before generic extraction
        name: str | None = None
        slug: str | None = None
        for keywords, rule_slug, rule_name in self._SLUG_OVERRIDES:
            if any(kw in lower_prompt for kw in keywords):
                slug = rule_slug
                name = rule_name
                break

        if name is None:
            name = _extract_name(prompt)
        if slug is None:
            slug = _to_slug(name)

        language = _detect_language(prompt)
        if slug in {"csv-cleaner", "json-schema-validator", "local-file-hasher"}:
            language = ToolLanguage.PYTHON
        category = _infer_category(prompt)
        tags = _extract_tags(prompt)

        # Generate parameters for known file-based tool types.
        if slug == "csv-cleaner":
            params: list[ParameterSpec] = [
                ParameterSpec(
                    name="input_path",
                    type="string",
                    description="Path to CSV file to clean (e.g., examples/input.csv)",
                    required=True,
                ),
                ParameterSpec(
                    name="output_path",
                    type="string",
                    description="Path where cleaned CSV will be written (e.g., outputs/cleaned.csv)",
                    required=False,
                    default="outputs/cleaned.csv",
                )
            ]
        elif slug == "json-schema-validator":
            params = [
                ParameterSpec(
                    name="data_path",
                    type="string",
                    description="Path to JSON data file to validate (e.g., examples/data_valid.json)",
                    required=True,
                ),
                ParameterSpec(
                    name="schema_path",
                    type="string",
                    description="Path to JSON schema file (e.g., examples/schema.json)",
                    required=True,
                ),
                ParameterSpec(
                    name="output_path",
                    type="string",
                    description="Path where validation report JSON is written",
                    required=False,
                    default="outputs/validation_report.json",
                ),
            ]
        elif slug == "local-file-hasher":
            params = [
                ParameterSpec(
                    name="file_path",
                    type="string",
                    description="Path to local file to hash (e.g., examples/sample.txt)",
                    required=True,
                ),
                ParameterSpec(
                    name="algorithm",
                    type="string",
                    description="Hash algorithm to use (md5, sha256, sha512)",
                    required=False,
                    default="sha256",
                ),
                ParameterSpec(
                    name="output_path",
                    type="string",
                    description="Optional path to write hash metadata JSON",
                    required=False,
                    default="outputs/hash_report.json",
                ),
            ]
        else:
            params = [
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

        # Build deterministic eval cases for known proof-path tools.
        if slug == "csv-cleaner":
            eval_cases = [
                EvalCase(
                    id="case-01-success",
                    description="Clean valid CSV file",
                    inputs={"input_path": "examples/input.csv"},
                    expected_success=True,
                    expected_output_contains="cleaned_path",
                    expected_files=[
                        EvalCase.ExpectedFile(path="outputs/cleaned.csv", should_exist=True)
                    ],
                    tags=["smoke"],
                ),
                EvalCase(
                    id="case-02-invalid-input",
                    description="Reject missing input file",
                    inputs={"input_path": "examples/missing.csv"},
                    expected_success=False,
                    expected_error_contains="not found",
                    tags=["edge-case"],
                ),
                EvalCase(
                    id="case-03-safety-boundary",
                    description="Path traversal attempt (should be blocked)",
                    inputs={"input_path": "../../../etc/passwd"},
                    expected_success=False,
                    expected_error_contains="Path validation failed",
                    tags=["safety"],
                ),
                EvalCase(
                    id="case-04-empty-file",
                    description="Empty CSV file",
                    inputs={
                        "input_path": "examples/empty.csv",
                        "output_path": "outputs/empty_cleaned.csv",
                    },
                    expected_success=True,
                    expected_files=[
                        EvalCase.ExpectedFile(
                            path="outputs/empty_cleaned.csv",
                            should_exist=True,
                        )
                    ],
                    tags=["edge-case"],
                ),
            ]
            eval_spec = EvalSpec(
                enabled=True,
                baseline_pass_rate=0.75,
                criteria=[
                    EvalCriterion(
                        name="no_error",
                        type=EvalCriterionType.NO_ERROR,
                        description="Tool runs without crashes",
                        weight=0.5,
                    ),
                    EvalCriterion(
                        name="expected_failures_caught",
                        type=EvalCriterionType.NO_ERROR,
                        description="Invalid-input and path-safety cases fail gracefully",
                        weight=0.5,
                    ),
                ],
                cases=eval_cases,
            )
        elif slug == "json-schema-validator":
            eval_cases = [
                EvalCase(
                    id="case-01-valid",
                    description="Validate correct JSON against schema",
                    inputs={
                        "data_path": "examples/data_valid.json",
                        "schema_path": "examples/schema.json",
                    },
                    expected_success=True,
                    expected_output_contains='"valid": true',
                    expected_files=[
                        EvalCase.ExpectedFile(path="outputs/validation_report.json", should_exist=True)
                    ],
                    tags=["smoke"],
                ),
                EvalCase(
                    id="case-02-invalid-data",
                    description="Invalid payload should produce validation errors",
                    inputs={
                        "data_path": "examples/data_invalid.json",
                        "schema_path": "examples/schema.json",
                        "output_path": "outputs/validation_invalid_report.json",
                    },
                    expected_success=True,
                    expected_output_contains='"valid": false',
                    expected_files=[
                        EvalCase.ExpectedFile(path="outputs/validation_invalid_report.json", should_exist=True)
                    ],
                    tags=["edge-case"],
                ),
                EvalCase(
                    id="case-03-safety-boundary",
                    description="Traversal attempt should be blocked",
                    inputs={
                        "data_path": "../../../etc/passwd",
                        "schema_path": "examples/schema.json",
                    },
                    expected_success=False,
                    expected_error_contains="Path validation failed",
                    tags=["safety"],
                ),
            ]
            eval_spec = EvalSpec(
                enabled=True,
                baseline_pass_rate=1.0,
                criteria=[
                    EvalCriterion(
                        name="no_error",
                        type=EvalCriterionType.NO_ERROR,
                        description="Tool runs without crashes for expected-success cases",
                        weight=1.0,
                    )
                ],
                cases=eval_cases,
            )
        elif slug == "local-file-hasher":
            eval_cases = [
                EvalCase(
                    id="case-01-success",
                    description="Hash sample file with default sha256",
                    inputs={"file_path": "examples/sample.txt"},
                    expected_success=True,
                    expected_output_contains='"algorithm": "sha256"',
                    tags=["smoke"],
                ),
                EvalCase(
                    id="case-02-with-output",
                    description="Hash sample file and write report",
                    inputs={
                        "file_path": "examples/sample.txt",
                        "algorithm": "sha512",
                        "output_path": "outputs/hash_report.json",
                    },
                    expected_success=True,
                    expected_output_contains='"algorithm": "sha512"',
                    expected_files=[
                        EvalCase.ExpectedFile(path="outputs/hash_report.json", should_exist=True)
                    ],
                    tags=["edge-case"],
                ),
                EvalCase(
                    id="case-03-safety-boundary",
                    description="Traversal attempt should be blocked",
                    inputs={"file_path": "../../../etc/passwd"},
                    expected_success=False,
                    expected_error_contains="Path validation failed",
                    tags=["safety"],
                ),
            ]
            eval_spec = EvalSpec(
                enabled=True,
                baseline_pass_rate=1.0,
                criteria=[
                    EvalCriterion(
                        name="no_error",
                        type=EvalCriterionType.NO_ERROR,
                        description="Tool runs without crashes for expected-success cases",
                        weight=1.0,
                    )
                ],
                cases=eval_cases,
            )
        else:
            eval_cases = [
                EvalCase(
                    id="case-01-success",
                    description="Basic tool invocation",
                    inputs={"input": "test_data"},
                    expected_success=True,
                    tags=["smoke"],
                )
            ]
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

        # Security spec with inferred permissions.
        if slug == "csv-cleaner":
            security_spec = SecuritySpec(
                requires_filesystem=True,
                requires_network=False,
                required_capabilities=[],
                allowed_read_paths=["./examples/**", "./inputs/**"],
                allowed_write_paths=["./outputs/**"],
                allowed_extensions=[".csv"],
                max_file_size_mb=50,
                privacy_level=PrivacyLevel.INTERNAL,
            )
        elif slug == "json-schema-validator":
            security_spec = SecuritySpec(
                requires_filesystem=True,
                requires_network=False,
                required_capabilities=[],
                allowed_read_paths=["./examples/**", "./inputs/**"],
                allowed_write_paths=["./outputs/**"],
                allowed_extensions=[".json"],
                max_file_size_mb=50,
                privacy_level=PrivacyLevel.INTERNAL,
            )
        elif slug == "local-file-hasher":
            security_spec = SecuritySpec(
                requires_filesystem=True,
                requires_network=False,
                required_capabilities=[],
                allowed_read_paths=["./examples/**", "./inputs/**"],
                allowed_write_paths=["./outputs/**"],
                allowed_extensions=[],
                max_file_size_mb=100,
                privacy_level=PrivacyLevel.INTERNAL,
            )
        else:
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
            dependencies=["jsonschema>=4.0"] if slug == "json-schema-validator" else [],
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
        if not data:
            raise ValueError("OpenAI response did not contain JSON content")
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
