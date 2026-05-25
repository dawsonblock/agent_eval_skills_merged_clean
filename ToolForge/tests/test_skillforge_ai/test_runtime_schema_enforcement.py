from __future__ import annotations
# mypy: disable-error-code=import-untyped

import json
from pathlib import Path

import pytest

from skillforge_ai.config import ensure_runtime_state, resolve_within_workspace
from skillforge_ai.skill_registry import SkillRegistry
from skillforge_ai.tool_registry import SkillForgeRegistry


def test_ensure_runtime_state_initializes_valid_permissions(
    tmp_path: Path,
) -> None:
    paths = ensure_runtime_state(tmp_path)

    payload = json.loads(paths.permissions_path.read_text(encoding="utf-8"))
    assert payload["version"] == "0.1.0"
    assert payload["default_mode"] == "interactive"
    assert payload["rules"] == []


def test_ensure_runtime_state_normalizes_invalid_files(tmp_path: Path) -> None:
    runtime = tmp_path / ".skillforge"
    runtime.mkdir(parents=True, exist_ok=True)
    (runtime / "registry.json").write_text(
        '{"bad": "shape"}\n',
        encoding="utf-8",
    )
    (runtime / "tool_registry.json").write_text(
        '[{"name": "bad"}]\n',
        encoding="utf-8",
    )
    (runtime / "permissions.json").write_text(
        '{"broken": true}\n',
        encoding="utf-8",
    )

    ensure_runtime_state(tmp_path)

    registry_payload = json.loads(
        (runtime / "registry.json").read_text(encoding="utf-8")
    )
    tools_payload = json.loads(
        (runtime / "tool_registry.json").read_text(encoding="utf-8")
    )
    perms_payload = json.loads(
        (runtime / "permissions.json").read_text(encoding="utf-8")
    )

    assert registry_payload == []
    assert tools_payload == []
    assert perms_payload["version"] == "0.1.0"


def test_skill_registry_rejects_invalid_name_pattern(tmp_path: Path) -> None:
    reg = SkillRegistry(tmp_path)
    with pytest.raises(Exception):
        reg.upsert({"name": "Bad Name With Spaces"})


def test_tool_registry_rejects_invalid_tool_shape(tmp_path: Path) -> None:
    reg = SkillForgeRegistry(tmp_path)
    with pytest.raises(Exception):
        reg.register_tool({"name": "csv_cleaner_tool"})


def test_config_detects_toolforge_root(tmp_path: Path) -> None:
    paths = ensure_runtime_state(tmp_path)
    assert paths.repo_root == tmp_path.resolve()
    assert paths.toolforge_root == tmp_path.resolve()
    assert paths.generated_tools_dir == tmp_path.resolve() / "tools" / "generated"


def test_config_uses_explicit_workspace_root(tmp_path: Path) -> None:
    explicit_root = tmp_path / "explicit"
    paths = ensure_runtime_state(explicit_root)
    assert paths.workspace_root == explicit_root.resolve()
    assert paths.skillforge_state_dir == explicit_root.resolve() / ".skillforge"


def test_paths_do_not_escape_workspace(tmp_path: Path) -> None:
    resolved = resolve_within_workspace(tmp_path, "skills/csv-cleaner")
    assert resolved == (tmp_path / "skills" / "csv-cleaner").resolve()
    with pytest.raises(ValueError):
        resolve_within_workspace(tmp_path, "../outside")
