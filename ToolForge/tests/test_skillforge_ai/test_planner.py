from __future__ import annotations

from skillforge_ai.planner import SkillPlanner


def test_planner_build_mode_and_csv_name():
    planner = SkillPlanner()
    result = planner.build_plan(
        "Build me a skill that cleans CSV files, trims whitespace, and exports JSON"
    )
    assert result.mode == "build_skill"
    assert result.skill_name == "csv-cleaner"
    assert result.requires_tool_code is True
    assert "tool/main.py" in result.files_to_create


def test_planner_repair_mode():
    planner = SkillPlanner()
    result = planner.build_plan("repair csv-cleaner")
    assert result.mode == "repair_skill"
    assert result.requires_tool_code is False
