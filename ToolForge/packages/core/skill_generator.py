"""
Skill generator — renders SKILL.md for a tool.

Creates:
  skills/generated/{category}/{slug}/SKILL.md
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from packages.core.tool_spec import ToolSpec
from packages.core.generator_utils import render_template, write_rendered, TOOLFORGE_VERSION


def generate_skill(spec: ToolSpec, output_root: Path, overwrite: bool = False) -> list[Path]:
    """
    Render a SKILL.md file for the tool described by *spec*.
    Writes to *output_root/{spec.skill.category}/{spec.slug}/SKILL.md*.
    """
    if not spec.skill.enabled:
        return []

    if output_root.name == "skill":
        skill_dir = output_root
    else:
        skill_dir = output_root / spec.skill.category / spec.slug
    skill_dir.mkdir(parents=True, exist_ok=True)

    ctx: dict[str, Any] = {"spec": spec, "toolforge_version": TOOLFORGE_VERSION}
    content = render_template("skill_template", "SKILL.md.j2", ctx)
    dest = skill_dir / "SKILL.md"
    if write_rendered(dest, content, overwrite):
        return [dest]
    return []
