from __future__ import annotations

from pathlib import Path

from skillforge_ai.package_manager import PackageManager


def run_package(workspace_root: Path, skill_name: str) -> dict[str, str]:
    zip_path, sha256 = PackageManager(workspace_root=workspace_root).package_skill(skill_name)
    return {"package_path": str(zip_path), "sha256": sha256}
