"""CLI regression tests for validation and new-tool UX behavior."""
from __future__ import annotations

from pathlib import Path

from apps.cli.toolforge_cli.test_helpers import combined_output, run_toolforge


def test_new_tool_duplicate_slug_fails_gracefully(tmp_path: Path) -> None:
    result = run_toolforge(["init", str(tmp_path)], cwd=tmp_path)
    assert result.returncode == 0, combined_output(result)

    first = run_toolforge(
        [
            "new",
            "tool",
            "--from-prompt",
            "Create a tool that cleans CSV files",
        ],
        cwd=tmp_path,
    )
    assert first.returncode == 0, combined_output(first)

    second = run_toolforge(
        [
            "new",
            "tool",
            "--from-prompt",
            "Create a tool that cleans CSV files",
        ],
        cwd=tmp_path,
    )
    assert second.returncode == 1
    output = combined_output(second)
    assert "Tool scaffold already exists" in output
    assert "--overwrite" in output


def test_validate_fails_when_tests_directory_missing(tmp_path: Path) -> None:
    result = run_toolforge(["init", str(tmp_path)], cwd=tmp_path)
    assert result.returncode == 0, combined_output(result)

    result = run_toolforge(
        [
            "new",
            "tool",
            "--from-prompt",
            "Create a tool that cleans CSV files",
        ],
        cwd=tmp_path,
    )
    assert result.returncode == 0, combined_output(result)

    tool_dir = tmp_path / "tools" / "generated" / "csv-cleaner"
    (tool_dir / "tests").rename(tool_dir / "tests_backup")

    mcp_result = run_toolforge(["generate", "mcp", "csv-cleaner"], cwd=tmp_path)
    assert mcp_result.returncode == 0, combined_output(mcp_result)

    skill_result = run_toolforge(["generate", "skill", "csv-cleaner"], cwd=tmp_path)
    assert skill_result.returncode == 0, combined_output(skill_result)

    eval_result = run_toolforge(["generate", "eval", "csv-cleaner"], cwd=tmp_path)
    assert eval_result.returncode == 0, combined_output(eval_result)

    validate = run_toolforge(["validate", "csv-cleaner"], cwd=tmp_path)
    assert validate.returncode == 1
    assert "Missing tests/ directory" in combined_output(validate)