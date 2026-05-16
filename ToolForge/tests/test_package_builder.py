"""Tests for package_builder exclusions and archive composition."""
from __future__ import annotations

import zipfile
from pathlib import Path
import pytest

from packages.core.package_builder import build_package
from packages.core.tool_spec import ParameterSpec, ToolLanguage, ToolSpec


def _spec() -> ToolSpec:
    return ToolSpec(
        name="Package Tool",
        slug="package-tool",
        version="0.1.0",
        description="Package test tool",
        language=ToolLanguage.PYTHON,
        entry_point="tool.py",
        parameters=[ParameterSpec(name="input", type="string", description="Input")],
    )


def _populate_required_structure(tool_dir: Path) -> None:
    (tool_dir / "README.md").write_text("# Package Tool\n", encoding="utf-8")
    (tool_dir / "SECURITY.md").write_text("# Security Notes\n", encoding="utf-8")
    (tool_dir / "tests").mkdir(parents=True, exist_ok=True)
    (tool_dir / "tests" / "test_smoke.py").write_text("def test_smoke():\n    assert True\n", encoding="utf-8")
    (tool_dir / "mcp").mkdir(parents=True, exist_ok=True)
    (tool_dir / "mcp" / "server.py").write_text("# mcp server\n", encoding="utf-8")
    (tool_dir / "skill").mkdir(parents=True, exist_ok=True)
    (tool_dir / "skill" / "SKILL.md").write_text("# Skill\n", encoding="utf-8")
    (tool_dir / "evals" / "cases").mkdir(parents=True, exist_ok=True)
    (tool_dir / "evals" / "task_config.json").write_text("{}\n", encoding="utf-8")
    (tool_dir / "evals" / "cases" / "case-01.json").write_text("{}\n", encoding="utf-8")


def test_package_excludes_runtime_outputs_dir(tmp_path: Path) -> None:
    spec = _spec()
    tool_dir = tmp_path / spec.slug
    dist_dir = tmp_path / "dist"
    tool_dir.mkdir(parents=True)

    spec.to_yaml(tool_dir / "toolforge.yaml")
    (tool_dir / "tool.py").write_text("def run(input: str = ''): return input\n", encoding="utf-8")
    _populate_required_structure(tool_dir)

    (tool_dir / "examples").mkdir(parents=True)
    (tool_dir / "examples" / "input.csv").write_text("name\nAlice\n", encoding="utf-8")

    (tool_dir / "outputs").mkdir(parents=True)
    (tool_dir / "outputs" / "cleaned.csv").write_text("name\nAlice\n", encoding="utf-8")

    archive = build_package(spec, tool_dir, dist_dir)

    assert archive.exists()
    with zipfile.ZipFile(archive) as zf:
        names = set(zf.namelist())

    assert "toolforge.yaml" in names
    assert "tool.py" in names
    assert "examples/input.csv" in names
    assert "outputs/cleaned.csv" not in names


def test_package_includes_skill_evals_and_security(tmp_path: Path) -> None:
    spec = _spec()
    tool_dir = tmp_path / spec.slug
    dist_dir = tmp_path / "dist"
    tool_dir.mkdir(parents=True)

    spec.to_yaml(tool_dir / "toolforge.yaml")
    (tool_dir / "tool.py").write_text("def run(input: str = ''): return input\n", encoding="utf-8")
    _populate_required_structure(tool_dir)

    (tool_dir / "examples").mkdir(parents=True)
    (tool_dir / "examples" / "input.csv").write_text("name\nAlice\n", encoding="utf-8")

    archive = build_package(spec, tool_dir, dist_dir)

    assert archive.exists()
    with zipfile.ZipFile(archive) as zf:
        names = set(zf.namelist())

    assert "skill/SKILL.md" in names
    assert "evals/task_config.json" in names
    assert "evals/cases/case-01.json" in names
    assert "SECURITY.md" in names


def test_package_fails_when_required_artifacts_missing(tmp_path: Path) -> None:
    spec = _spec()
    tool_dir = tmp_path / spec.slug
    dist_dir = tmp_path / "dist"
    tool_dir.mkdir(parents=True)

    spec.to_yaml(tool_dir / "toolforge.yaml")
    (tool_dir / "tool.py").write_text("def run(input: str = ''): return input\n", encoding="utf-8")

    with pytest.raises(FileNotFoundError):
        build_package(spec, tool_dir, dist_dir)
