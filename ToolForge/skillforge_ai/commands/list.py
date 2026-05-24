from __future__ import annotations

from pathlib import Path

from skillforge_ai.tool_registry import SkillForgeRegistry


def run_list(workspace_root: Path) -> list[dict]:
    return SkillForgeRegistry(workspace_root=workspace_root).list_skills()
