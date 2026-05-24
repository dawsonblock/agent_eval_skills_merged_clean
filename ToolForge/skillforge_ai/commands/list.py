from __future__ import annotations

from pathlib import Path

from skillforge_ai.skill_registry import SkillRegistry


def run_list(workspace_root: Path) -> list[dict]:
    return SkillRegistry(workspace_root=workspace_root).list()
