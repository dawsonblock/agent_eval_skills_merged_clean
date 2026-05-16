"""Unit tests for path safety validation."""
from __future__ import annotations

from pathlib import Path

import pytest

from packages.core.path_safety import PathViolationError, validate_all_path_inputs
from packages.core.tool_spec import SecuritySpec


@pytest.fixture
def security() -> SecuritySpec:
    return SecuritySpec(
        requires_filesystem=True,
        allowed_read_paths=["./examples/**"],
        allowed_write_paths=["./outputs/**"],
        blocked_paths=["/etc/**", "~/.ssh/**", ".env", ".env.*"],
        allowed_extensions=[".csv"],
        allow_symlinks=False,
        max_file_size_mb=1,
    )


def test_accepts_valid_read_and_write_paths(tmp_path: Path, security: SecuritySpec) -> None:
    examples = tmp_path / "examples"
    examples.mkdir()
    (examples / "input.csv").write_text("name\nAlice\n", encoding="utf-8")

    validate_all_path_inputs(
        {
            "input_path": "examples/input.csv",
            "output_path": "outputs/cleaned.csv",
        },
        security,
        tmp_path,
    )


def test_rejects_path_traversal(tmp_path: Path, security: SecuritySpec) -> None:
    with pytest.raises(PathViolationError):
        validate_all_path_inputs({"input_path": "../../../etc/passwd"}, security, tmp_path)


def test_rejects_write_outside_allowed_root(tmp_path: Path, security: SecuritySpec) -> None:
    examples = tmp_path / "examples"
    examples.mkdir()
    (examples / "input.csv").write_text("name\nAlice\n", encoding="utf-8")

    with pytest.raises(PathViolationError):
        validate_all_path_inputs(
            {
                "input_path": "examples/input.csv",
                "output_path": "../../outside.csv",
            },
            security,
            tmp_path,
        )


def test_rejects_disallowed_extension(tmp_path: Path, security: SecuritySpec) -> None:
    examples = tmp_path / "examples"
    examples.mkdir()
    (examples / "input.txt").write_text("hello", encoding="utf-8")

    with pytest.raises(PathViolationError):
        validate_all_path_inputs({"input_path": "examples/input.txt"}, security, tmp_path)


def test_rejects_symlink_when_disabled(tmp_path: Path, security: SecuritySpec) -> None:
    examples = tmp_path / "examples"
    examples.mkdir()
    real = examples / "real.csv"
    real.write_text("name\nAlice\n", encoding="utf-8")
    link = examples / "link.csv"
    link.symlink_to(real)

    with pytest.raises(PathViolationError):
        validate_all_path_inputs({"input_path": "examples/link.csv"}, security, tmp_path)


def test_accepts_data_and_schema_paths_for_json_tools(tmp_path: Path) -> None:
    security = SecuritySpec(
        requires_filesystem=True,
        allowed_read_paths=["./examples/**"],
        allowed_write_paths=["./outputs/**"],
        allowed_extensions=[".json"],
    )
    examples = tmp_path / "examples"
    examples.mkdir()
    (examples / "data.json").write_text('{"ok": true}', encoding="utf-8")
    (examples / "schema.json").write_text('{"type": "object"}', encoding="utf-8")

    validate_all_path_inputs(
        {
            "data_path": "examples/data.json",
            "schema_path": "examples/schema.json",
            "output_path": "outputs/report.json",
        },
        security,
        tmp_path,
    )
