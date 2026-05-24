from __future__ import annotations

from pathlib import Path

from skillforge_ai.planner import SkillPlanner
from skillforge_ai.skill_builder import SkillBuilder


def run_create(workspace_root: Path, prompt: str, provider: str = "rule_based") -> dict[str, str]:
    planner = SkillPlanner()
    plan = planner.build_plan(prompt)
    builder = SkillBuilder(workspace_root=workspace_root, provider=provider)
    tool_dir, manifest = builder.build(prompt, skill_name=plan.skill_name)
    return {"skill_name": manifest.name, "tool_dir": str(tool_dir), "mode": plan.mode}
