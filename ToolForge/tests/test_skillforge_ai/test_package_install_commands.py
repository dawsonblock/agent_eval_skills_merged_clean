from __future__ import annotations

import json
import zipfile
from pathlib import Path

from skillforge_ai.commands.install import run_install
from skillforge_ai.commands.package import run_package


def _make_generated_tool(tmp_path: Path, slug: str) -> Path:
    tool_dir = tmp_path / "tools" / "generated" / slug
    tool_dir.mkdir(parents=True, exist_ok=True)
    (tool_dir / "tool.py").write_text("print('ok')\n", encoding="utf-8")
    return tool_dir


def _make_skill_layout(tmp_path: Path, slug: str) -> Path:
    skill_dir = tmp_path / "skills" / slug
    (skill_dir / "tool").mkdir(parents=True, exist_ok=True)
    (skill_dir / "tests").mkdir(parents=True, exist_ok=True)
    (skill_dir / "examples").mkdir(parents=True, exist_ok=True)

    (skill_dir / "SKILL.md").write_text("# Skill\n", encoding="utf-8")
    (skill_dir / "README.md").write_text("# README\n", encoding="utf-8")
    (skill_dir / "metadata.json").write_text("{}\n", encoding="utf-8")
    (skill_dir / "validation_report.json").write_text("{}\n", encoding="utf-8")
    (skill_dir / "tool" / "main.py").write_text("print('ok')\n", encoding="utf-8")
    (skill_dir / "tests" / "test_basic.py").write_text(
        "def test_basic():\n    assert True\n",
        encoding="utf-8",
    )
    (skill_dir / "examples" / "sample.csv").write_text("a,b\n1,2\n", encoding="utf-8")
    return skill_dir


def test_run_package_records_hash_in_skill_registry(tmp_path: Path):
    slug = "csv-cleaner"
    _make_generated_tool(tmp_path, slug)

    output, sha = run_package(tmp_path, slug, output=None)

    assert output.exists()
    assert len(sha) == 64

    registry_path = tmp_path / ".skillforge" / "registry.json"
    payload = json.loads(registry_path.read_text(encoding="utf-8"))
    entry = next(item for item in payload if item["name"] == slug)
    assert entry["package_hash"] == sha
    assert entry["status"] == "packaged"

    provenance_path = tmp_path / ".skillforge" / "provenance" / "toolforge_provenance.json"
    assert provenance_path.exists()
    provenance = json.loads(provenance_path.read_text(encoding="utf-8"))
    assert provenance["skill"] == slug
    assert provenance["packaging_mode"] == "tool_archive"
    assert provenance["package"]["sha256"] == sha


def test_run_package_prefers_skill_layout_package_dir(tmp_path: Path):
    slug = "csv-cleaner"
    _make_generated_tool(tmp_path, slug)
    _make_skill_layout(tmp_path, slug)

    output, sha = run_package(tmp_path, slug, output=None)

    assert output.exists()
    assert len(sha) == 64
    assert ".skillforge/packages/" in output.as_posix()

    provenance_path = tmp_path / ".skillforge" / "provenance" / "toolforge_provenance.json"
    provenance = json.loads(provenance_path.read_text(encoding="utf-8"))
    assert provenance["packaging_mode"] == "skill_layout"
    assert provenance["package"]["path"] == str(output)


def test_run_package_skill_layout_output_override_updates_registry(tmp_path: Path):
    slug = "csv-cleaner"
    _make_generated_tool(tmp_path, slug)
    _make_skill_layout(tmp_path, slug)

    output_target = tmp_path / "dist" / "custom-output.zip"
    output, sha = run_package(tmp_path, slug, output=output_target)

    assert output == output_target
    assert output.exists()
    assert len(sha) == 64

    registry_path = tmp_path / ".skillforge" / "registry.json"
    payload = json.loads(registry_path.read_text(encoding="utf-8"))
    entry = next(item for item in payload if item["name"] == slug)
    assert entry["package_path"] == str(output_target)
    assert entry["package_hash"] == sha
    assert entry["status"] == "packaged"


def test_run_install_records_hash_and_tool_registry(tmp_path: Path):
    slug = "csv-cleaner"
    archive = tmp_path / f"{slug}-0.1.0.zip"

    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("tool.py", "print('ok')\n")

    installed_slug, dest, sha = run_install(tmp_path, archive)

    assert installed_slug == slug
    assert dest.exists()
    assert len(sha) == 64

    skill_registry = json.loads(
        (tmp_path / ".skillforge" / "registry.json").read_text(encoding="utf-8")
    )
    skill_entry = next(item for item in skill_registry if item["name"] == slug)
    assert skill_entry["installed_hash"] == sha
    assert skill_entry["status"] == "installed"

    tool_registry = json.loads(
        (tmp_path / ".skillforge" / "tool_registry.json").read_text(encoding="utf-8")
    )
    assert any(item["name"] == f"{slug}_tool" for item in tool_registry)
