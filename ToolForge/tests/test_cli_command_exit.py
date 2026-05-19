"""Focused CLI command-exit tests for hang-prone paths.

Each test uses a fresh tmp_path workspace and executes exactly one subprocess
command under test. Setup is done via internal Python APIs to keep subprocess
nesting shallow and deterministic.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from tests.e2e_scripts._lifecycle import (
    create_workspace,
    generate_eval,
    generate_mcp,
    generate_skill,
    generate_tool_from_prompt,
)
from tests.e2e_scripts._process import assert_no_toolforge_children, run_process_tree

ROOT = Path(__file__).parent.parent
CSV_PROMPT = "Create a tool that cleans CSV files"
JSON_PROMPT = "Create a tool that validates JSON files against a schema"
HASH_PROMPT = "Create a tool that computes SHA256 hashes for local files"


def _clean_env(root: Path) -> dict[str, str]:
    env = os.environ.copy()
    for key in (
        "PYTEST_CURRENT_TEST",
        "PYTEST_VERSION",
        "PYTEST_ADDOPTS",
        "PYTEST_PLUGINS",
        "COVERAGE_PROCESS_START",
    ):
        env.pop(key, None)
    env["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PYTHONUNBUFFERED"] = "1"
    env["TOOLFORGE_TEST_USE_MODULE_CLI"] = "1"

    paths = [str(root), str(root / "apps" / "cli")]
    existing = env.get("PYTHONPATH", "")
    if existing:
        paths.append(existing)
    env["PYTHONPATH"] = os.pathsep.join(paths)
    return env


def _run_command(
    args: list[str],
    *,
    cwd: Path,
    timeout: int,
) -> subprocess.CompletedProcess[str]:
    env = _clean_env(ROOT)
    return run_process_tree(
        [sys.executable, "-m", "apps.cli.toolforge_cli.main", *args],
        cwd=cwd,
        env=env,
        timeout=timeout,
    )


def _setup_csv(workspace: Path, *, include_validate: bool) -> None:
    workspace = create_workspace(workspace)
    generate_tool_from_prompt(workspace, CSV_PROMPT)
    generate_mcp(workspace, "csv-cleaner")
    generate_skill(workspace, "csv-cleaner")
    generate_eval(workspace, "csv-cleaner")
    if include_validate:
        result = _run_command(["validate", "csv-cleaner"], cwd=workspace, timeout=180)
        assert result.returncode == 0, result.stdout + result.stderr


def test_new_tool_command_exits(tmp_path: Path) -> None:
    workspace = create_workspace(tmp_path)
    result = _run_command(
        ["new", "tool", "--from-prompt", CSV_PROMPT],
        cwd=workspace,
        timeout=120,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert (workspace / "tools" / "generated" / "csv-cleaner" / "tool.py").exists()
    assert_no_toolforge_children()


def test_validate_csv_tool_command_exits(tmp_path: Path) -> None:
    workspace = create_workspace(tmp_path)
    generate_tool_from_prompt(workspace, CSV_PROMPT)
    generate_mcp(workspace, "csv-cleaner")
    generate_skill(workspace, "csv-cleaner")
    generate_eval(workspace, "csv-cleaner")

    result = _run_command(["validate", "csv-cleaner"], cwd=workspace, timeout=180)
    output = result.stdout + result.stderr
    assert result.returncode == 0, output
    assert "All validations passed" in output
    assert_no_toolforge_children()


def test_package_csv_tool_command_exits(tmp_path: Path) -> None:
    # Keep setup minimal: package command does not require prior validation.
    workspace = create_workspace(tmp_path)
    generate_tool_from_prompt(workspace, CSV_PROMPT)
    generate_mcp(workspace, "csv-cleaner")
    generate_skill(workspace, "csv-cleaner")
    generate_eval(workspace, "csv-cleaner")

    result = _run_command(["package", "csv-cleaner"], cwd=workspace, timeout=180)
    output = result.stdout + result.stderr
    assert result.returncode == 0, output
    assert "Package built" in output
    assert (workspace / "dist" / "csv-cleaner-0.1.0.zip").exists()
    assert_no_toolforge_children()


def test_package_json_tool_command_exits(tmp_path: Path) -> None:
    workspace = create_workspace(tmp_path)
    generate_tool_from_prompt(workspace, JSON_PROMPT)
    generate_mcp(workspace, "json-schema-validator")
    generate_skill(workspace, "json-schema-validator")
    generate_eval(workspace, "json-schema-validator")

    result = _run_command(["package", "json-schema-validator"], cwd=workspace, timeout=180)
    assert result.returncode == 0, result.stdout + result.stderr
    assert (workspace / "dist" / "json-schema-validator-0.1.0.zip").exists()
    assert_no_toolforge_children()


def test_package_hasher_tool_command_exits(tmp_path: Path) -> None:
    workspace = create_workspace(tmp_path)
    generate_tool_from_prompt(workspace, HASH_PROMPT)
    generate_mcp(workspace, "local-file-hasher")
    generate_skill(workspace, "local-file-hasher")
    generate_eval(workspace, "local-file-hasher")

    result = _run_command(["package", "local-file-hasher"], cwd=workspace, timeout=180)
    assert result.returncode == 0, result.stdout + result.stderr
    assert (workspace / "dist" / "local-file-hasher-0.1.0.zip").exists()
    assert_no_toolforge_children()
