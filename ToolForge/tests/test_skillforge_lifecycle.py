from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from skillforge_ai.models import ValidationReport
from skillforge_ai.planner import SkillPlanner
from skillforge_ai.validation_runner import ValidationRunner


def _make_tool_dir(root: Path, slug: str) -> None:
    tool_dir = root / "tools" / "generated" / slug
    tool_dir.mkdir(parents=True, exist_ok=True)
    (tool_dir / "toolforge.yaml").write_text("name: csv-cleaner\n", encoding="utf-8")


def test_planner_lifecycle_boundaries_for_non_build_modes() -> None:
    planner = SkillPlanner()

    validate_plan = planner.build_plan("validate workspace")
    package_plan = planner.build_plan("package csv-cleaner")

    assert validate_plan.mode == "validate_workspace"
    assert validate_plan.requires_tool_code is False
    assert "write_files" not in validate_plan.permissions

    assert package_plan.mode == "package_skill"
    assert package_plan.requires_tool_code is False
    assert "write_files" in package_plan.permissions


def test_planner_build_mode_requires_tool_code_and_write_access() -> None:
    planner = SkillPlanner()
    build_plan = planner.build_plan("create a tool that cleans csv files")

    assert build_plan.mode == "build_skill"
    assert build_plan.requires_tool_code is True
    assert "write_files" in build_plan.permissions


def test_validation_runner_repair_loop_honors_max_attempt_limit(tmp_path: Path) -> None:
    slug = "csv-cleaner"
    _make_tool_dir(tmp_path, slug)

    runner = ValidationRunner(workspace_root=tmp_path, max_repair_attempts=2)

    fail1 = ValidationReport(slug=slug, passed=False, attempt=1, errors=["Schema: bad"])
    fail2 = ValidationReport(slug=slug, passed=False, attempt=2, errors=["Schema: bad"])
    fail3 = ValidationReport(slug=slug, passed=False, attempt=3, errors=["Schema: bad"])

    with patch.object(
        runner,
        "validate",
        side_effect=[fail1, fail2, fail3],
    ) as validate_mock, patch.object(
        runner,
        "_repair",
        return_value=None,
    ) as repair_mock:
        final_report = runner.repair_loop(slug, provider="rule_based")

    assert final_report.passed is False
    assert validate_mock.call_count == 3
    assert repair_mock.call_count == 2
