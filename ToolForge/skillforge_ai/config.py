from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class SkillForgePaths:
    workspace_root: Path

    @property
    def runtime_root(self) -> Path:
        return self.workspace_root / ".skillforge"

    @property
    def registry_path(self) -> Path:
        return self.runtime_root / "registry.json"

    @property
    def tool_registry_path(self) -> Path:
        return self.runtime_root / "tool_registry.json"

    @property
    def permissions_path(self) -> Path:
        return self.runtime_root / "permissions.json"

    @property
    def runs_dir(self) -> Path:
        return self.runtime_root / "runs"

    @property
    def evidence_dir(self) -> Path:
        return self.runtime_root / "evidence"

    @property
    def packages_dir(self) -> Path:
        return self.runtime_root / "packages"

    @property
    def skills_dir(self) -> Path:
        return self.workspace_root / "skills"


def ensure_runtime_state(workspace_root: Path) -> SkillForgePaths:
    paths = SkillForgePaths(workspace_root=workspace_root.resolve())
    paths.runtime_root.mkdir(parents=True, exist_ok=True)
    paths.runs_dir.mkdir(parents=True, exist_ok=True)
    paths.evidence_dir.mkdir(parents=True, exist_ok=True)
    paths.packages_dir.mkdir(parents=True, exist_ok=True)

    if not paths.registry_path.exists():
        paths.registry_path.write_text("[]\n", encoding="utf-8")
    if not paths.tool_registry_path.exists():
        paths.tool_registry_path.write_text("[]\n", encoding="utf-8")
    if not paths.permissions_path.exists():
        paths.permissions_path.write_text("{}\n", encoding="utf-8")

    return paths
