"""CLI regression tests for validation and new-tool UX behavior."""
from __future__ import annotations

import os
import sys
from pathlib import Path

from tests.e2e_scripts._process import assert_no_toolforge_children, run_process_tree
from tests.e2e_scripts._runner import build_clean_env, run_toolforge


ROOT = Path(__file__).parent.parent


def combined_output(stdout: str, stderr: str) -> str:
    return (stdout or "") + ("\n" + stderr if stderr else "")


def test_new_tool_duplicate_slug_fails_gracefully(tmp_path: Path) -> None:
    result = run_toolforge(["init", str(tmp_path)], cwd=tmp_path, check=False)
    assert result.returncode == 0, combined_output(result.stdout, result.stderr)

    first = run_toolforge(
        [
            "new",
            "tool",
            "--from-prompt",
            "Create a tool that cleans CSV files",
        ],
        cwd=tmp_path,
        check=False,
    )
    assert first.returncode == 0, combined_output(first.stdout, first.stderr)

    second = run_toolforge(
        [
            "new",
            "tool",
            "--from-prompt",
            "Create a tool that cleans CSV files",
        ],
        cwd=tmp_path,
        check=False,
    )
    assert second.returncode == 1
    output = combined_output(second.stdout, second.stderr)
    assert "Tool scaffold already exists" in output
    assert "--overwrite" in output
    assert_no_toolforge_children()


def test_validate_fails_when_tests_directory_missing(tmp_path: Path) -> None:
    script = ROOT / "tests" / "e2e_scripts" / "run_validation_missing_tests_regression.py"
    env = build_clean_env()
    result = run_process_tree(
        [sys.executable, str(script), str(tmp_path)],
        cwd=ROOT,
        env=env,
        timeout=180,
    )
    output = combined_output(result.stdout, result.stderr)
    assert result.returncode == 0, output
    assert "Missing tests/ directory" in output
    assert_no_toolforge_children()