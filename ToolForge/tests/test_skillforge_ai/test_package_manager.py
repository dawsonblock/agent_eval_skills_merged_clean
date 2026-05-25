from __future__ import annotations
# mypy: disable-error-code=import-untyped

import json
from pathlib import Path

from skillforge_ai.package_manager import PackageManager


def _write_skill(tmp_path: Path, slug: str) -> None:
    skill_dir = tmp_path / "skills" / slug
    (skill_dir / "tool").mkdir(parents=True, exist_ok=True)
    (skill_dir / "tests").mkdir(parents=True, exist_ok=True)
    (skill_dir / "examples").mkdir(parents=True, exist_ok=True)
    (skill_dir / "SKILL.md").write_text("# Skill\n", encoding="utf-8")
    (skill_dir / "metadata.json").write_text("{}\n", encoding="utf-8")
    (skill_dir / "README.md").write_text("# Readme\n", encoding="utf-8")
    (skill_dir / "tool" / "main.py").write_text(
        "print('ok')\n", encoding="utf-8"
    )
    (skill_dir / "tests" / "test_basic.py").write_text(
        "def test_ok():\n    assert True\n", encoding="utf-8"
    )


def test_package_manager_builds_zip_and_hash(tmp_path: Path):
    _write_skill(tmp_path, "csv-cleaner")

    manager = PackageManager(tmp_path)
    zip_path, sha = manager.package_skill("csv-cleaner")

    assert zip_path.exists()
    assert len(sha) == 64

    registry_path = tmp_path / ".skillforge" / "registry.json"
    payload = json.loads(registry_path.read_text(encoding="utf-8"))
    assert payload[0]["name"] == "csv-cleaner"
    assert payload[0]["package_hash"] == sha


def test_package_manager_uses_deterministic_filename(tmp_path: Path):
    _write_skill(tmp_path, "csv-cleaner")

    manager = PackageManager(tmp_path)
    zip_path, _ = manager.package_skill("csv-cleaner")

    assert zip_path.name == "csv-cleaner-0.1.0.zip"
