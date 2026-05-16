"""
Skill validator — checks SKILL.md structure against the toolforge schema.

Ported from:
  legacy/agent-skills-curated/evals/validators/structural.js
"""
from __future__ import annotations

import re
from pathlib import Path

# Required top-level sections every SKILL.md must contain
REQUIRED_SECTIONS = [
    "Purpose",
    "Use When",
    "Do Not Use When",
    "Inputs",
    "Outputs",
    "Safety Rules",
    "Procedure",
    "Validation Checklist",
    "Failure Modes",
    "Examples",
]

# YAML frontmatter keys that must be present
REQUIRED_FRONTMATTER_KEYS = {"name", "description"}


def validate_skill_file(skill_path: Path) -> list[str]:
    """
    Validate a SKILL.md at *skill_path*.
    Returns a list of error strings (empty = valid).
    """
    errors: list[str] = []

    if not skill_path.exists():
        return [f"SKILL.md not found: {skill_path}"]

    content = skill_path.read_text(encoding="utf-8")

    # --- Frontmatter check ---
    fm_match = re.match(r"^---\n(.*?)\n---", content, re.DOTALL)
    if not fm_match:
        errors.append("Missing YAML frontmatter (expected opening and closing ---)")
    else:
        fm_text = fm_match.group(1)
        for key in REQUIRED_FRONTMATTER_KEYS:
            if not re.search(rf'^{re.escape(key)}\s*:', fm_text, re.MULTILINE):
                errors.append(f"Frontmatter missing required key: '{key}'")

    # --- Section check ---
    for section in REQUIRED_SECTIONS:
        if not re.search(rf'^#+\s+{re.escape(section)}', content, re.MULTILINE | re.IGNORECASE):
            errors.append(f"Missing required section: '## {section}'")

    # --- Minimum length ---
    if len(content.strip()) < 200:
        errors.append("SKILL.md is too short (< 200 characters); likely incomplete")

    return errors
