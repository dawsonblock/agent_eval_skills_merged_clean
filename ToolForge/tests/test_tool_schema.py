"""Unit tests for packages.core.tool_schema."""
from __future__ import annotations

import json

import pytest

from packages.core.tool_schema import build_toolforge_yaml_schema, validate_spec_dict


def test_schema_has_required_keys() -> None:
    schema = build_toolforge_yaml_schema()
    assert "properties" in schema
    props = schema["properties"]
    for key in ("name", "slug", "version", "description", "language", "entry_point"):
        assert key in props, f"Expected property '{key}' in schema"


def test_validate_valid_spec() -> None:
    d = {
        "name": "My Tool",
        "slug": "my-tool",
        "version": "0.1.0",
        "description": "A tool",
        "language": "python",
        "entry_point": "tool.py",
    }
    # Should not raise
    validate_spec_dict(d)


def test_validate_missing_required_field() -> None:
    d = {
        "name": "My Tool",
        # missing slug, version, etc.
    }
    with pytest.raises(Exception):
        validate_spec_dict(d)


def test_schema_is_json_serialisable() -> None:
    schema = build_toolforge_yaml_schema()
    assert json.dumps(schema)  # should not raise
