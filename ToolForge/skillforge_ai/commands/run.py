from __future__ import annotations

from pathlib import Path

from packages.runners.tool_runner import run_tool
from packages.validators.schema_validator import validate_yaml_file


def run_skill(workspace_root: Path, slug: str, inputs: dict[str, str]):
    tool_dir = workspace_root.resolve() / "tools" / "generated" / slug
    spec = validate_yaml_file(tool_dir / "toolforge.yaml")
    return run_tool(spec, tool_dir, inputs)
