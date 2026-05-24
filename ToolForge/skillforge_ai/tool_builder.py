from __future__ import annotations

from pathlib import Path

from skillforge_ai.planner import PlannerResult
from skillforge_ai.skill_builder import SkillBuilder


class ToolBuilder:
    """Python-first tool generation wrapper over existing SkillBuilder."""

    def __init__(self, workspace_root: Path, provider: str = "rule_based") -> None:
        self._workspace_root = workspace_root
        self._provider = provider

    def build_python_tool(self, plan: PlannerResult) -> Path:
        builder = SkillBuilder(
            workspace_root=self._workspace_root,
            provider=self._provider,
            generate_mcp=plan.requires_mcp,
            generate_eval_harness=True,
        )
        tool_dir, _manifest = builder.build(
            request=f"Create a Python tool named {plan.skill_name} that satisfies: {plan.intent}",
            skill_name=plan.skill_name,
        )
        return tool_dir
