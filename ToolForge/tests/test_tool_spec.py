"""Unit tests for packages.core.tool_spec."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from packages.core.tool_spec import (
    EvalCase,
    EvalCriterion,
    EvalCriterionType,
    EvalSpec,
    MCPSpec,
    ParameterSpec,
    PrivacyLevel,
    SandboxLevel,
    SecuritySpec,
    SkillSpec,
    ToolCapability,
    ToolLanguage,
    ToolSpec,
)


def _minimal_spec(**kwargs) -> ToolSpec:
    defaults = dict(name="My Tool", slug="my-tool", version="0.1.0", description="A tool", language=ToolLanguage.PYTHON, entry_point="tool.py")
    defaults.update(kwargs)
    return ToolSpec(**defaults)


# ---------------------------------------------------------------------------
# Enum smoke tests
# ---------------------------------------------------------------------------

def test_tool_language_values() -> None:
    assert ToolLanguage.PYTHON.value == "python"
    assert ToolLanguage.TYPESCRIPT.value == "typescript"


def test_sandbox_level_ordering() -> None:
    assert SandboxLevel.NONE < SandboxLevel.DOCKER_NO_NETWORK


def test_eval_criterion_type_values() -> None:
    types = {e.value for e in EvalCriterionType}
    assert "exact_match" in types
    assert "no_error" in types
    assert "semantic_similarity" in types
    assert "performance" in types


# ---------------------------------------------------------------------------
# ParameterSpec
# ---------------------------------------------------------------------------

def test_parameter_spec_required_default() -> None:
    p = ParameterSpec(name="x", type="string", description="X param")
    assert p.required is True


def test_parameter_spec_optional() -> None:
    p = ParameterSpec(name="y", type="integer", description="Y", required=False, default="0")
    assert p.required is False


# ---------------------------------------------------------------------------
# ToolSpec construction
# ---------------------------------------------------------------------------

def test_minimal_spec_builds() -> None:
    spec = _minimal_spec()
    assert spec.slug == "my-tool"


def test_required_params() -> None:
    spec = _minimal_spec(
        parameters=[
            ParameterSpec(name="a", type="string", description="A", required=True),
            ParameterSpec(name="b", type="string", description="B", required=False),
        ]
    )
    req = spec.required_params()
    opt = spec.optional_params()
    assert len(req) == 1 and req[0].name == "a"
    assert len(opt) == 1 and opt[0].name == "b"


def test_to_json_schema_inputs() -> None:
    spec = _minimal_spec(
        parameters=[
            ParameterSpec(name="path", type="string", description="File path", required=True),
        ]
    )
    schema = spec.to_json_schema_inputs()
    assert schema["type"] == "object"
    assert "path" in schema["properties"]
    assert "path" in schema["required"]


# ---------------------------------------------------------------------------
# Serialisation round-trip
# ---------------------------------------------------------------------------

def test_yaml_round_trip(tmp_path: Path) -> None:
    spec = _minimal_spec(tags=["test"])
    yaml_path = tmp_path / "tool.yaml"
    spec.to_yaml(yaml_path)
    loaded = ToolSpec.from_yaml(yaml_path)
    assert loaded.slug == spec.slug
    assert loaded.tags == spec.tags


def test_from_yaml_missing_file() -> None:
    with pytest.raises(FileNotFoundError):
        ToolSpec.from_yaml(Path("/nonexistent/toolforge.yaml"))
