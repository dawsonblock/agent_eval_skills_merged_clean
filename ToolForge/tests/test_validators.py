"""Unit tests for the validators package."""
from __future__ import annotations

from pathlib import Path

import pytest

from packages.core.tool_spec import ToolLanguage, ToolSpec
from packages.validators.schema_validator import SchemaValidationError, validate_yaml_file
from packages.validators.security_validator import SecurityViolation, validate_security
from packages.validators.skill_validator import validate_skill_file


# ---------------------------------------------------------------------------
# SchemaValidator
# ---------------------------------------------------------------------------

def test_schema_validator_valid_yaml(tmp_path: Path) -> None:
    yaml_path = tmp_path / "toolforge.yaml"
    yaml_path.write_text(
        "name: My Tool\nslug: my-tool\nversion: '0.1.0'\ndescription: A tool\nlanguage: python\nentry_point: tool.py\n",
        encoding="utf-8",
    )
    spec = validate_yaml_file(yaml_path)
    assert isinstance(spec, ToolSpec)
    assert spec.slug == "my-tool"


def test_schema_validator_invalid_yaml(tmp_path: Path) -> None:
    yaml_path = tmp_path / "toolforge.yaml"
    yaml_path.write_text("name: Incomplete\n", encoding="utf-8")
    with pytest.raises(SchemaValidationError):
        validate_yaml_file(yaml_path)


def test_schema_validator_missing_file() -> None:
    with pytest.raises(FileNotFoundError):
        validate_yaml_file(Path("/nonexistent/toolforge.yaml"))


# ---------------------------------------------------------------------------
# SecurityValidator
# ---------------------------------------------------------------------------

def _make_spec(**kwargs) -> ToolSpec:
    defaults = dict(
        name="Sec Tool",
        slug="sec-tool",
        version="0.1.0",
        description="Security test tool",
        language=ToolLanguage.PYTHON,
        entry_point="tool.py",
    )
    defaults.update(kwargs)
    return ToolSpec(**defaults)


def test_security_validator_no_violations() -> None:
    spec = _make_spec()
    violations = validate_security(spec)
    assert isinstance(violations, list)


# ---------------------------------------------------------------------------
# SkillValidator
# ---------------------------------------------------------------------------

_VALID_SKILL = """\
---
name: My Skill
description: Does something useful.
---
## Overview
What this skill does.

## Usage
How to use it.

## Parameters
None.

## Output
A string.

## Examples
Example 1.

## When to Use
When you need it.

## Security
No sensitive data.

## Tags
general
"""


def test_skill_validator_valid(tmp_path: Path) -> None:
    skill_md = tmp_path / "SKILL.md"
    skill_md.write_text(_VALID_SKILL, encoding="utf-8")
    errors = validate_skill_file(skill_md)
    assert errors == [], f"Unexpected errors: {errors}"


def test_skill_validator_missing_section(tmp_path: Path) -> None:
    skill_md = tmp_path / "SKILL.md"
    skill_md.write_text("---\nname: X\ndescription: Y\n---\n## Overview\nHi\n", encoding="utf-8")
    errors = validate_skill_file(skill_md)
    assert len(errors) > 0


def test_skill_validator_missing_frontmatter_key(tmp_path: Path) -> None:
    skill_md = tmp_path / "SKILL.md"
    # Missing 'description' key
    content = "---\nname: X\n---\n" + "\n".join(f"## {s}\nContent\n" for s in
        ["Overview", "Usage", "Parameters", "Output", "Examples", "When to Use", "Security", "Tags"])
    skill_md.write_text(content, encoding="utf-8")
    errors = validate_skill_file(skill_md)
    assert any("description" in e.lower() for e in errors)
