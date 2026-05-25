from __future__ import annotations
# mypy: disable-error-code=import-untyped

from pathlib import Path

from skillforge_ai.skill_registry import SkillRegistry
from skillforge_ai.tool_registry import SkillForgeRegistry


def run_inspect(workspace_root: Path, skill_name: str) -> dict | None:
    skill = SkillRegistry(workspace_root).get(skill_name)
    if skill is not None:
        return skill
    return SkillForgeRegistry(workspace_root=workspace_root).get_skill(
        skill_name
    )
