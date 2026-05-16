"""Tests for json-schema-validator tool."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))
from tool import validate_json  # noqa: E402


def test_valid_data() -> None:
    result = validate_json(
        '{"name": "Alice", "age": 30}',
        '{"type": "object", "properties": {"name": {"type": "string"}}, "required": ["name"]}',
    )
    assert result["valid"] is True
    assert result["errors"] == []


def test_missing_required_field() -> None:
    result = validate_json(
        '{"age": 30}',
        '{"type": "object", "required": ["name"]}',
    )
    assert result["valid"] is False
    assert len(result["errors"]) >= 1


def test_wrong_type() -> None:
    result = validate_json(
        '{"name": 123}',
        '{"type": "object", "properties": {"name": {"type": "string"}}}',
    )
    assert result["valid"] is False


def test_invalid_json_data() -> None:
    result = validate_json("not json at all !!!", '{"type": "object"}')
    assert result["valid"] is False
    assert any("parse" in e.lower() for e in result["errors"])


def test_file_path(tmp_path: Path) -> None:
    data_file = tmp_path / "data.json"
    schema_file = tmp_path / "schema.json"
    data_file.write_text('{"x": 1}', encoding="utf-8")
    schema_file.write_text('{"type": "object"}', encoding="utf-8")

    result = validate_json(str(data_file), str(schema_file))
    assert result["valid"] is True
