"""Focused CLI command exit tests for hang-prone commands.

Each test verifies that exactly one CLI command exits reliably without hanging.

Setup for every test uses the _lifecycle.py internal Python API (pure Python,
no subprocess) so that setup completes in < 0.5 s.  Only the single command
under test runs as a subprocess with an explicit process-tree timeout.

Proven generator slugs only — no generic/AI prompts:
  csv-cleaner
  json-schema-validator
  local-file-hasher
"""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path

from tests.e2e_scripts._lifecycle import (
    create_workspace,
    generate_eval,
    generate_mcp,
    generate_skill,
    generate_tool_from_prompt,
)
from tests.e2e_scripts._process import run_process_tree

# ---------------------------------------------------------------------------
# Repository root — parent of this file's tests/ directory
# ---------------------------------------------------------------------------
ROOT = Path(__file__).parent.parent


# ---------------------------------------------------------------------------
# Environment builder
# ---------------------------------------------------------------------------

def build_clean_env(root: Path) -> dict[str, str]:
    """Build a clean environment for CLI subprocess execution.

    Strips pytest env-contamination vars, sets PYTHONPATH so that
    `python -m apps.cli.toolforge_cli.main` is importable, and marks the
    subprocess as a test CLI invocation.
    """
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


# ---------------------------------------------------------------------------
# Tiny CLI helper — run one toolforge command with process-tree timeout
# ---------------------------------------------------------------------------

def _cli(
    args: list[str],
    cwd: Path,
    env: dict[str, str],
    timeout: int,
) -> "subprocess.CompletedProcess[str]":
    """Run `toolforge <args>` via module path with process-tree timeout."""
    return run_process_tree(
        [sys.executable, "-m", "apps.cli.toolforge_cli.main", *args],
        cwd=cwd,
        env=env,
        timeout=timeout,
    )


# ---------------------------------------------------------------------------
# Fast tests — registry/eval on empty or known workspace (no subprocess setup)
# ---------------------------------------------------------------------------

def test_registry_list_exits_cleanly() -> None:
    """registry list exits cleanly in an empty workspace (no tools registered)."""
    env = build_clean_env(ROOT)
    with tempfile.TemporaryDirectory() as tmp_dir:
        workspace = create_workspace(Path(tmp_dir))
        r = _cli(["registry", "list"], workspace, env, 30)
        assert r.returncode == 0
        assert (
            "No tools registered" in r.stdout
            or "Registered Tools" in r.stdout
        ), f"Unexpected registry list output:\n{r.stdout}"


def test_registry_info_missing_exits_cleanly() -> None:
    """registry info for a non-existent tool exits non-zero without hanging."""
    env = build_clean_env(ROOT)
    with tempfile.TemporaryDirectory() as tmp_dir:
        workspace = create_workspace(Path(tmp_dir))
        r = _cli(["registry", "info", "csv-cleaner"], workspace, env, 30)
        assert r.returncode != 0


def test_registry_info_with_tool_exits_cleanly() -> None:
    """registry info exits cleanly after a tool has been registered.

    This is the scenario observed hanging in the demo: registry info
    called after the full tool lifecycle (new → generate → validate →
    run → package).  Internal setup simulates a post-register state.
    """
    env = build_clean_env(ROOT)
    with tempfile.TemporaryDirectory() as tmp_dir:
        workspace = create_workspace(Path(tmp_dir))
        # Register csv-cleaner via internal API (fast, no subprocess)
        generate_tool_from_prompt(workspace, "Create a tool that cleans CSV files")
        r = _cli(["registry", "info", "csv-cleaner"], workspace, env, 30)
        # Should print info and exit; any returncode is acceptable, must not hang
        assert r.returncode is not None


def test_eval_missing_tool_exits_cleanly() -> None:
    """eval on a non-existent tool exits non-zero without hanging."""
    env = build_clean_env(ROOT)
    with tempfile.TemporaryDirectory() as tmp_dir:
        workspace = create_workspace(Path(tmp_dir))
        r = _cli(["eval", "csv-cleaner"], workspace, env, 30)
        assert r.returncode != 0


# ---------------------------------------------------------------------------
# new tool tests — subprocess only, one per proven slug
# These specifically test that `toolforge new tool` exits cleanly.
# ---------------------------------------------------------------------------

def test_new_csv_tool_command_exits() -> None:
    """new tool --from-prompt (csv-cleaner) exits cleanly via subprocess."""
    env = build_clean_env(ROOT)
    with tempfile.TemporaryDirectory() as tmp_dir:
        workspace = create_workspace(Path(tmp_dir))
        r = _cli(
            ["new", "tool", "--from-prompt", "Create a tool that cleans CSV files"],
            workspace, env, 120,
        )
        assert r.returncode == 0, (
            f"stdout:\n{r.stdout}\nstderr:\n{r.stderr}"
        )


def test_new_json_tool_command_exits() -> None:
    """new tool --from-prompt (json-schema-validator) exits cleanly via subprocess."""
    env = build_clean_env(ROOT)
    with tempfile.TemporaryDirectory() as tmp_dir:
        workspace = create_workspace(Path(tmp_dir))
        r = _cli(
            [
                "new", "tool", "--from-prompt",
                "Create a tool that validates JSON files against a schema",
            ],
            workspace, env, 120,
        )
        assert r.returncode == 0, (
            f"stdout:\n{r.stdout}\nstderr:\n{r.stderr}"
        )


def test_new_hasher_tool_command_exits() -> None:
    """new tool --from-prompt (local-file-hasher) exits cleanly via subprocess."""
    env = build_clean_env(ROOT)
    with tempfile.TemporaryDirectory() as tmp_dir:
        workspace = create_workspace(Path(tmp_dir))
        r = _cli(
            [
                "new", "tool", "--from-prompt",
                "Create a tool that computes SHA256 hashes for local files",
            ],
            workspace, env, 120,
        )
        assert r.returncode == 0, (
            f"stdout:\n{r.stdout}\nstderr:\n{r.stderr}"
        )


# ---------------------------------------------------------------------------
# Single-command tests — internal full-artifact setup, one subprocess command
# ---------------------------------------------------------------------------

def test_validate_csv_tool_command_exits() -> None:
    """validate csv-cleaner exits cleanly without hanging.

    Setup (init + scaffold + mcp + skill + eval) is done via the internal
    Python API so it completes in < 1 s and is never a hang source.
    """
    env = build_clean_env(ROOT)
    with tempfile.TemporaryDirectory() as tmp_dir:
        workspace = create_workspace(Path(tmp_dir))
        generate_tool_from_prompt(workspace, "Create a tool that cleans CSV files")
        generate_mcp(workspace, "csv-cleaner")
        generate_skill(workspace, "csv-cleaner")
        generate_eval(workspace, "csv-cleaner")
        r = _cli(["validate", "csv-cleaner"], workspace, env, 120)
        # Exit code may be 0 (all pass) or non-zero (some check failed).
        # The important invariant is that the command returns rather than hangs.
        assert r.returncode is not None


def test_run_csv_tool_command_exits() -> None:
    """run csv-cleaner with valid input exits cleanly without hanging."""
    env = build_clean_env(ROOT)
    with tempfile.TemporaryDirectory() as tmp_dir:
        workspace = create_workspace(Path(tmp_dir))
        generate_tool_from_prompt(workspace, "Create a tool that cleans CSV files")
        r = _cli(
            ["run", "csv-cleaner", "--input", "input_path=examples/input.csv"],
            workspace, env, 60,
        )
        assert r.returncode is not None


def test_package_csv_tool_command_exits() -> None:
    """package csv-cleaner exits cleanly without hanging."""
    env = build_clean_env(ROOT)
    with tempfile.TemporaryDirectory() as tmp_dir:
        workspace = create_workspace(Path(tmp_dir))
        generate_tool_from_prompt(workspace, "Create a tool that cleans CSV files")
        generate_mcp(workspace, "csv-cleaner")
        generate_skill(workspace, "csv-cleaner")
        generate_eval(workspace, "csv-cleaner")
        r = _cli(["package", "csv-cleaner"], workspace, env, 60)
        assert r.returncode is not None


def test_eval_csv_command_exits() -> None:
    """eval csv-cleaner exits cleanly without hanging.

    Only the tool is scaffolded (no eval artifacts), so the command fails
    fast with a missing-artifact error.  The key invariant is no hang.
    """
    env = build_clean_env(ROOT)
    with tempfile.TemporaryDirectory() as tmp_dir:
        workspace = create_workspace(Path(tmp_dir))
        generate_tool_from_prompt(workspace, "Create a tool that cleans CSV files")
        r = _cli(["eval", "csv-cleaner"], workspace, env, 60)
        assert r.returncode is not None


# ---------------------------------------------------------------------------
# JSON package — the previously-observed timeout case, tested in full isolation
# ---------------------------------------------------------------------------

def test_json_package_command_exits() -> None:
    """toolforge package json-schema-validator exits cleanly without hanging.

    Generates full artifact set (mcp + skill + eval) via internal API so
    that package has everything it needs to run the full zip-build path.
    """
    env = build_clean_env(ROOT)
    with tempfile.TemporaryDirectory() as tmp_dir:
        workspace = create_workspace(Path(tmp_dir))
        generate_tool_from_prompt(
            workspace,
            "Create a tool that validates JSON files against a schema",
        )
        generate_mcp(workspace, "json-schema-validator")
        generate_skill(workspace, "json-schema-validator")
        generate_eval(workspace, "json-schema-validator")
        r = _cli(["package", "json-schema-validator"], workspace, env, 90)
        assert r.returncode is not None
