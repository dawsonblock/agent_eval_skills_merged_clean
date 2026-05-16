"""Unit tests for packages.core.skill_generator."""
from __future__ import annotations

from pathlib import Path

from packages.core.skill_generator import generate_skill
from packages.core.tool_spec import SkillSpec, ToolLanguage, ToolSpec


def _make_spec(category: str = "general") -> ToolSpec:
    return ToolSpec(
        name="Skill Tool",
        slug="skill-tool",
        version="0.1.0",
        description="A test skill tool",
        language=ToolLanguage.PYTHON,
        entry_point="tool.py",
        skill=SkillSpec(enabled=True, category=category),
    )


def test_generates_skill_md(tmp_path: Path) -> None:
    spec = _make_spec()
    created = generate_skill(spec, tmp_path)
    names = {p.name for p in created}
    assert "SKILL.md" in names


def test_skill_md_under_category(tmp_path: Path) -> None:
    spec = _make_spec(category="coding-agents-and-ides")
    created = generate_skill(spec, tmp_path)
    for p in created:
        assert "coding-agents-and-ides" in str(p)


def test_skill_md_contains_name(tmp_path: Path) -> None:
    spec = _make_spec()
    created = generate_skill(spec, tmp_path)
    skill_md = next(p for p in created if p.name == "SKILL.md")
    content = skill_md.read_text(encoding="utf-8")
    assert spec.name in content


def test_skill_md_contains_required_sections(tmp_path: Path) -> None:
    spec = _make_spec()
    created = generate_skill(spec, tmp_path)
    skill_md = next(p for p in created if p.name == "SKILL.md")
    content = skill_md.read_text(encoding="utf-8")
    for section in ("Overview", "Usage", "Parameters", "Output", "Examples"):
        assert section in content, f"Missing section: {section}"
