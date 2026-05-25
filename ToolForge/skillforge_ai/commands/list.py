from __future__ import annotations
# mypy: disable-error-code=import-untyped

from pathlib import Path

from skillforge_ai.skill_registry import SkillRegistry
from skillforge_ai.tool_registry import SkillForgeRegistry


def run_list(workspace_root: Path) -> list[dict]:
    skill_entries = SkillRegistry(workspace_root).list()
    if skill_entries:
        return skill_entries
    return SkillForgeRegistry(workspace_root=workspace_root).list_skills()
