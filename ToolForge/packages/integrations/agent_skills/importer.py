"""
agent_skills importer — port legacy SKILL.md files into the ToolForge workspace.
"""

from __future__ import annotations

import shutil
from pathlib import Path


def import_skill(skill_path: Path, skills_root: Path) -> list[Path]:
    """
    Copy a legacy SKILL.md (or a skill directory) into *skills_root*.

    Accepts either:
      - Path to a SKILL.md file
      - Path to a directory containing a SKILL.md

    The destination is placed under::
      skills_root / <category> / <slug> / SKILL.md

    where *category* and *slug* are inferred from the parent directory
    names of *skill_path*.

    Returns list of Path objects that were created.
    """
    if skill_path.is_file():
        skill_md = skill_path
        skill_dir = skill_path.parent
    else:
        skill_md = skill_path / "SKILL.md"
        skill_dir = skill_path

    if not skill_md.exists():
        raise FileNotFoundError(f"No SKILL.md found at {skill_md}")

    slug = skill_dir.name
    # Try to infer category from grandparent directory
    category_candidate = skill_dir.parent.name
    if category_candidate in ("skills", "generated", "."):
        category = "general"
    else:
        category = category_candidate

    dest_dir = skills_root / category / slug
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest_md = dest_dir / "SKILL.md"

    shutil.copy2(skill_md, dest_md)
    created = [dest_md]

    # Copy any extra assets in the skill directory (non-SKILL.md files)
    for extra in skill_dir.iterdir():
        if extra.name == "SKILL.md" or extra.is_dir():
            continue
        shutil.copy2(extra, dest_dir / extra.name)
        created.append(dest_dir / extra.name)

    return created
