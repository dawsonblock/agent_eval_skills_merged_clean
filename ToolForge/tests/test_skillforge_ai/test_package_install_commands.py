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
