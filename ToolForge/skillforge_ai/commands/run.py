from __future__ import annotations

from pathlib import Path

from packages.runners.tool_runner import run_tool
from packages.validators.schema_validator import validate_yaml_file
from skillforge_ai.skill_registry import SkillRegistry


def run_skill(workspace_root: Path, slug: str, inputs: dict[str, str]):
    root = workspace_root.resolve()
    registry = SkillRegistry(root)
    if registry.get(slug) is None:
        raise ValueError(f"Skill '{slug}' is not registered. Register or install it before running.")

    tool_dir = root / "tools" / "generated" / slug
    if not tool_dir.exists():
        raise FileNotFoundError(f"Tool directory not found for '{slug}': {tool_dir}")

    spec = validate_yaml_file(tool_dir / "toolforge.yaml")
    return run_tool(spec, tool_dir, inputs)
