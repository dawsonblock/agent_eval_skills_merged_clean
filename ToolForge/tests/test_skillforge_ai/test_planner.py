from __future__ import annotations

from skillforge_ai.planner import SkillPlanner


def test_planner_build_mode_and_csv_name():
    planner = SkillPlanner()
    result = planner.build_plan(
        (
            "Build me a skill that cleans CSV files, trims whitespace, "
            "and exports JSON"
        )
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


def test_planner_call_tool_mode():
    planner = SkillPlanner()
    result = planner.build_plan("tools call csv-cleaner csv_cleaner_tool")
    assert result.mode == "call_tool"
    assert "tool registry lookup" in result.validation_plan


def test_planner_validate_workspace_mode():
    planner = SkillPlanner()
    result = planner.build_plan("validate workspace")
    assert result.mode == "validate_workspace"
    assert result.intent == "validate_workspace"


def test_planner_infers_browser_category():
    planner = SkillPlanner()
    result = planner.build_plan(
        "Build a skill to scrape tables from a website URL"
    )
    assert result.category == "browser"


def test_planner_falls_back_to_custom_category():
    planner = SkillPlanner()
    result = planner.build_plan("Build me something unusual and bespoke")
    assert result.category == "custom"
