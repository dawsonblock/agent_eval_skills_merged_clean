from __future__ import annotations

from pathlib import Path

from skillforge_ai.skill_registry import SkillRegistry


def run_inspect(workspace_root: Path, skill_name: str) -> dict | None:
    return SkillRegistry(workspace_root=workspace_root).get(skill_name)
