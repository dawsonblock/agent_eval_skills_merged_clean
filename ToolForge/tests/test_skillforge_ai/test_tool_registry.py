"""
Tests for skillforge_ai.tool_registry — SkillForgeRegistry CRUD operations.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from skillforge_ai.models import SkillManifest
from skillforge_ai.tool_registry import SkillForgeRegistry


def _write_empty_registry(tmp_path: Path) -> Path:
    reg_path = tmp_path / "toolforge_registry.json"
    reg_path.write_text("{}", encoding="utf-8")
    return reg_path


def _make_manifest(name: str = "csv-cleaner") -> SkillManifest:
    return SkillManifest(
        name=name,
        description=f"Cleans CSV files ({name})",
        category="data",
        risk_level="low",
    )


class TestSkillForgeRegistryCRUD:
    def test_list_skills_empty(self, tmp_path: Path):
        _write_empty_registry(tmp_path)
        reg = SkillForgeRegistry(tmp_path)
        assert reg.list_skills() == []

    def test_register_and_list(self, tmp_path: Path):
        _write_empty_registry(tmp_path)
        tool_dir = tmp_path / "tools" / "generated" / "csv-cleaner"
        tool_dir.mkdir(parents=True)

        reg = SkillForgeRegistry(tmp_path)
        manifest = _make_manifest()
        reg.register_skill(manifest, tool_dir)

        skills = reg.list_skills()
        assert len(skills) == 1
        assert skills[0]["name"] == "csv-cleaner"

    def test_get_skill_returns_dict(self, tmp_path: Path):
        _write_empty_registry(tmp_path)
        tool_dir = tmp_path / "tools" / "generated" / "csv-cleaner"
        tool_dir.mkdir(parents=True)

        reg = SkillForgeRegistry(tmp_path)
        reg.register_skill(_make_manifest(), tool_dir)

        skill = reg.get_skill("csv-cleaner")
        assert skill is not None
        assert skill["name"] == "csv-cleaner"

    def test_get_skill_missing_returns_none(self, tmp_path: Path):
        _write_empty_registry(tmp_path)
        reg = SkillForgeRegistry(tmp_path)
        assert reg.get_skill("nonexistent") is None

    def test_mark_validated(self, tmp_path: Path):
        _write_empty_registry(tmp_path)
        tool_dir = tmp_path / "tools" / "generated" / "csv-cleaner"
        tool_dir.mkdir(parents=True)

        reg = SkillForgeRegistry(tmp_path)
        reg.register_skill(_make_manifest(), tool_dir)
        reg.mark_validated("csv-cleaner")

        skill = reg.get_skill("csv-cleaner")
        assert skill["validated"] is True

    def test_mark_failed(self, tmp_path: Path):
        _write_empty_registry(tmp_path)
        tool_dir = tmp_path / "tools" / "generated" / "csv-cleaner"
        tool_dir.mkdir(parents=True)

        reg = SkillForgeRegistry(tmp_path)
        reg.register_skill(_make_manifest(), tool_dir)
        reg.mark_failed("csv-cleaner", error="schema error")

        skill = reg.get_skill("csv-cleaner")
        assert skill["status"] in ("failed", "validation_failed")

    def test_mark_packaged(self, tmp_path: Path):
        _write_empty_registry(tmp_path)
        tool_dir = tmp_path / "tools" / "generated" / "csv-cleaner"
        tool_dir.mkdir(parents=True)

        reg = SkillForgeRegistry(tmp_path)
        reg.register_skill(_make_manifest(), tool_dir)
        reg.mark_packaged("csv-cleaner")

        skill = reg.get_skill("csv-cleaner")
        assert skill["status"] == "packaged"

    def test_list_tools_returns_list(self, tmp_path: Path):
        _write_empty_registry(tmp_path)
        tool_dir = tmp_path / "tools" / "generated" / "csv-cleaner"
        tool_dir.mkdir(parents=True)

        reg = SkillForgeRegistry(tmp_path)
        reg.register_skill(_make_manifest(), tool_dir)

        tools = reg.list_tools()
        assert isinstance(tools, list)
        assert len(tools) >= 1

    def test_register_multiple_skills(self, tmp_path: Path):
        _write_empty_registry(tmp_path)

        reg = SkillForgeRegistry(tmp_path)
        for name in ("skill-a", "skill-b", "skill-c"):
            tool_dir = tmp_path / "tools" / "generated" / name
            tool_dir.mkdir(parents=True)
            reg.register_skill(_make_manifest(name), tool_dir)

        assert len(reg.list_skills()) == 3

    def test_schema_keys_present(self, tmp_path: Path):
        _write_empty_registry(tmp_path)
        tool_dir = tmp_path / "tools" / "generated" / "csv-cleaner"
        tool_dir.mkdir(parents=True)

        reg = SkillForgeRegistry(tmp_path)
        reg.register_skill(_make_manifest(), tool_dir)

        skill = reg.get_skill("csv-cleaner")
        required_keys = {"name", "type", "description", "entrypoint", "permissions",
                         "risk_level", "validated", "mcp_server", "status", "category"}
        assert required_keys.issubset(set(skill.keys()))
