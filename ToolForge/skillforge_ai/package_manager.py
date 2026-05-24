from __future__ import annotations

import hashlib
import json
import zipfile
from datetime import datetime
from pathlib import Path

from skillforge_ai.config import ensure_runtime_state
from skillforge_ai.skill_registry import SkillRegistry


class PackageManager:
    def __init__(self, workspace_root: Path) -> None:
        self._paths = ensure_runtime_state(workspace_root)
        self._registry = SkillRegistry(workspace_root)

    def package_skill(self, skill_name: str, version: str = "0.1.0") -> tuple[Path, str]:
        skill_dir = self._paths.skills_dir / skill_name
        if not skill_dir.exists():
            raise FileNotFoundError(f"Skill not found: {skill_dir}")

        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        zip_path = self._paths.packages_dir / f"{skill_name}-{version}-{ts}.zip"

        include_names = {
            "SKILL.md",
            "metadata.json",
            "README.md",
            "validation_report.json",
        }
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for file_path in skill_dir.rglob("*"):
                if not file_path.is_file():
                    continue
                rel = file_path.relative_to(skill_dir)
                if rel.parts[0] in {"tool", "tests", "examples"} or rel.name in include_names:
                    zf.write(file_path, rel)

        sha256 = self._sha256(zip_path)
        existing = self._registry.get(skill_name) or {"name": skill_name}
        existing["package_hash"] = sha256
        existing["package_path"] = str(zip_path)
        self._registry.upsert(existing)
        return zip_path, sha256

    @staticmethod
    def _sha256(path: Path) -> str:
        h = hashlib.sha256()
        with path.open("rb") as fh:
            for chunk in iter(lambda: fh.read(65536), b""):
                h.update(chunk)
        return h.hexdigest()
