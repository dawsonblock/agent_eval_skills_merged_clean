from __future__ import annotations

from pathlib import Path

from skillforge_ai.tool_registry import SkillForgeRegistry


def run_inspect(workspace_root: Path, skill_name: str) -> dict | None:
    return SkillForgeRegistry(workspace_root=workspace_root).get_skill(skill_name)
