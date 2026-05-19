"""Focused CLI command exit tests for hang-prone commands.

Each test verifies that exactly one CLI command exits reliably without hanging.

A module-scoped fixture pre-builds a complete csv-cleaner workspace (tool +
MCP + skill + eval) so that per-command tests (validate, run, package, eval)
only need to run the single command under test rather than regenerating the
tool from scratch each time.  Tests that exercise the *new tool* path each
create their own isolated workspace.

Proven generator slugs only:
  csv-cleaner
  json-schema-validator
  local-file-hasher

Generic/AI prompts that produce unstable scaffolds are not used here.
"""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Generator

import pytest

from tests.e2e_scripts._process import run_process_tree

# ---------------------------------------------------------------------------
# Repository root — parent of this file's directory
# ---------------------------------------------------------------------------
ROOT = Path(__file__).parent.parent


# ---------------------------------------------------------------------------
# Environment builder
# ---------------------------------------------------------------------------

def build_clean_env(root: Path) -> dict[str, str]:
    """Build a clean environment for CLI subprocess execution.

    Strips pytest env-contamination vars, sets PYTHONPATH so that
    `python -m apps.cli.toolforge_cli.main` is importable, and marks
    the subprocess as a test CLI invocation.
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
# Tiny helper — run one CLI command with process-tree timeout
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
# Module-scoped fixture — builds a complete csv-cleaner workspace ONCE
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def csv_workspace(
    tmp_path_factory: pytest.TempPathFactory,
) -> Generator[tuple[Path, dict[str, str]], None, None]:
    """Module-scoped fixture: complete csv-cleaner workspace.

    Generates the tool once per test-module run and shares the workspace
    directory across all single-command tests, avoiding redundant
    subprocess-based tool generation.

    Setup: init → new tool → generate mcp → generate skill → generate eval
    Each step uses run_process_tree with an individual timeout so a hung
    command raises ProcessTimeoutError and fails the fixture immediately
    rather than hanging the whole suite.
    """
    tmp = tmp_path_factory.mktemp("cmd_exit_csv_")
    env = build_clean_env(ROOT)

    r = _cli(["init", str(tmp)], ROOT, env, 30)
    assert r.returncode == 0, (
        f"workspace init failed\nstdout:\n{r.stdout}\nstderr:\n{r.stderr}"
    )

    r = _cli(
        ["new", "tool", "--from-prompt", "Create a tool that cleans CSV files"],
        tmp, env, 120,
    )
    assert r.returncode == 0, (
        f"new tool (csv-cleaner) failed\nstdout:\n{r.stdout}\nstderr:\n{r.stderr}"
    )

    # Generate all artifacts; failures here are non-fatal for the fixture —
    # downstream tests that need these artifacts will see non-zero exit codes
    # and assert returncode is not None (i.e. they verify no hang, not success).
    _cli(["generate", "mcp", "csv-cleaner"], tmp, env, 60)
    _cli(["generate", "skill", "csv-cleaner"], tmp, env, 60)
    _cli(["generate", "eval", "csv-cleaner"], tmp, env, 60)

    yield tmp, env


# ---------------------------------------------------------------------------
# Fast tests — no tool generation, init only
# ---------------------------------------------------------------------------

def test_registry_list_exits_cleanly() -> None:
    """registry list exits cleanly in an empty workspace (no tools registered)."""
    env = build_clean_env(ROOT)
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp = Path(tmp_dir)
        r = _cli(["init", str(tmp)], ROOT, env, 30)
        assert r.returncode == 0
        r = _cli(["registry", "list"], tmp, env, 30)
        assert r.returncode == 0
        assert (
            "No tools registered" in r.stdout
            or "Registered Tools" in r.stdout
        ), f"Unexpected registry list output:\n{r.stdout}"


def test_registry_info_missing_exits_cleanly() -> None:
    """registry info for a non-existent tool exits non-zero without hanging."""
    env = build_clean_env(ROOT)
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp = Path(tmp_dir)
        r = _cli(["init", str(tmp)], ROOT, env, 30)
        assert r.returncode == 0
        r = _cli(["registry", "info", "csv-cleaner"], tmp, env, 30)
        assert r.returncode != 0


def test_eval_missing_tool_exits_cleanly() -> None:
    """eval on a non-existent tool exits non-zero without hanging."""
    env = build_clean_env(ROOT)
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp = Path(tmp_dir)
        r = _cli(["init", str(tmp)], ROOT, env, 30)
        assert r.returncode == 0
        r = _cli(["eval", "csv-cleaner"], tmp, env, 30)
        assert r.returncode != 0


# ---------------------------------------------------------------------------
# New-tool tests — one per proven slug, independent workspaces
# ---------------------------------------------------------------------------

def test_new_csv_tool_command_exits() -> None:
    """new tool --from-prompt (csv-cleaner) exits cleanly."""
    env = build_clean_env(ROOT)
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp = Path(tmp_dir)
        r = _cli(["init", str(tmp)], ROOT, env, 30)
        assert r.returncode == 0
        r = _cli(
            ["new", "tool", "--from-prompt", "Create a tool that cleans CSV files"],
            tmp, env, 120,
        )
        assert r.returncode == 0, (
            f"stdout:\n{r.stdout}\nstderr:\n{r.stderr}"
        )


def test_new_json_tool_command_exits() -> None:
    """new tool --from-prompt (json-schema-validator) exits cleanly."""
    env = build_clean_env(ROOT)
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp = Path(tmp_dir)
        r = _cli(["init", str(tmp)], ROOT, env, 30)
        assert r.returncode == 0
        r = _cli(
            [
                "new", "tool", "--from-prompt",
                "Create a tool that validates JSON files against a schema",
            ],
            tmp, env, 120,
        )
        assert r.returncode == 0, (
            f"stdout:\n{r.stdout}\nstderr:\n{r.stderr}"
        )


def test_new_hasher_tool_command_exits() -> None:
    """new tool --from-prompt (local-file-hasher) exits cleanly."""
    env = build_clean_env(ROOT)
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp = Path(tmp_dir)
        r = _cli(["init", str(tmp)], ROOT, env, 30)
        assert r.returncode == 0
        r = _cli(
            [
                "new", "tool", "--from-prompt",
                "Create a tool that computes SHA256 hashes for local files",
            ],
            tmp, env, 120,
        )
        assert r.returncode == 0, (
            f"stdout:\n{r.stdout}\nstderr:\n{r.stderr}"
        )


# ---------------------------------------------------------------------------
# Single-command tests that share the pre-built csv workspace
# ---------------------------------------------------------------------------

def test_validate_csv_tool_command_exits(
    csv_workspace: tuple[Path, dict[str, str]],
) -> None:
    """validate csv-cleaner exits cleanly without hanging.

    Exit code may be 0 (all checks pass) or non-zero (some artifact missing),
    but the command MUST return and not hang.
    """
    tmp, env = csv_workspace
    r = _cli(["validate", "csv-cleaner"], tmp, env, 90)
    assert r.returncode is not None


def test_run_csv_tool_command_exits(
    csv_workspace: tuple[Path, dict[str, str]],
) -> None:
    """run csv-cleaner with valid input exits cleanly without hanging."""
    tmp, env = csv_workspace
    r = _cli(
        ["run", "csv-cleaner", "--input", "input_path=examples/input.csv"],
        tmp, env, 60,
    )
    assert r.returncode is not None


def test_package_csv_tool_command_exits(
    csv_workspace: tuple[Path, dict[str, str]],
) -> None:
    """package csv-cleaner exits cleanly without hanging."""
    tmp, env = csv_workspace
    r = _cli(["package", "csv-cleaner"], tmp, env, 60)
    assert r.returncode is not None


def test_eval_csv_command_exits(
    csv_workspace: tuple[Path, dict[str, str]],
) -> None:
    """eval csv-cleaner exits cleanly without hanging.

    Eval cases may not all pass (depends on runtime state), but the
    eval command must return rather than block indefinitely.
    """
    tmp, env = csv_workspace
    r = _cli(["eval", "csv-cleaner"], tmp, env, 90)
    assert r.returncode is not None


# ---------------------------------------------------------------------------
# JSON package — the known trouble case, verified in full isolation
# ---------------------------------------------------------------------------

def test_json_package_command_exits() -> None:
    """toolforge package json-schema-validator exits cleanly without hanging.

    This test exercises the full JSON package path including all artifact
    generation to reproduce the previously observed timeout.
    """
    env = build_clean_env(ROOT)
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp = Path(tmp_dir)
        r = _cli(["init", str(tmp)], ROOT, env, 30)
        assert r.returncode == 0

        r = _cli(
            [
                "new", "tool", "--from-prompt",
                "Create a tool that validates JSON files against a schema",
            ],
            tmp, env, 120,
        )
        assert r.returncode == 0, (
            f"stdout:\n{r.stdout}\nstderr:\n{r.stderr}"
        )

        # Generate full artifact set so package can succeed
        _cli(["generate", "mcp", "json-schema-validator"], tmp, env, 60)
        _cli(["generate", "skill", "json-schema-validator"], tmp, env, 60)
        _cli(["generate", "eval", "json-schema-validator"], tmp, env, 60)

        r = _cli(["package", "json-schema-validator"], tmp, env, 90)
        # Must exit — non-zero is acceptable if artifacts are incomplete
        assert r.returncode is not None
