"""Test registry CLI commands exit reliably without hanging.

Tool setup uses the _lifecycle.py internal Python API (no subprocess) so
tests complete in < 5 s each.  Only the registry CLI commands themselves
are exercised as subprocesses.
"""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path

from tests.e2e_scripts._lifecycle import create_workspace, generate_tool_from_prompt
from tests.e2e_scripts._process import run_process_tree

ROOT = Path(__file__).parent.parent


def _build_env(root: Path) -> dict[str, str]:
    """Build a clean subprocess environment with correct PYTHONPATH."""
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


def _cli(
    args: list[str],
    cwd: Path,
    timeout: int,
) -> subprocess.CompletedProcess[str]:
    """Run `toolforge <args>` via module path with process-tree timeout."""
    return run_process_tree(
        [sys.executable, "-m", "apps.cli.toolforge_cli.main", *args],
        cwd=cwd,
        env=_build_env(ROOT),
        timeout=timeout,
    )


def test_registry_list_exits_cleanly() -> None:
    """registry list exits cleanly after a tool has been registered.

    Tool registration uses the internal Python API (no subprocess) so the
    setup is instant and cannot be a hang source.
    """
    with tempfile.TemporaryDirectory() as tmp_dir:
        workspace = create_workspace(Path(tmp_dir))
        # Register csv-cleaner via internal Python API — fast, no subprocess
        generate_tool_from_prompt(workspace, "Create a tool that cleans CSV files")

        r = _cli(["registry", "list"], workspace, 30)
        assert r.returncode == 0
        assert "csv-cleaner" in r.stdout.lower()


def test_registry_info_exits_cleanly() -> None:
    """registry info exits cleanly for a registered tool.

    Tool registration uses the internal Python API (no subprocess).
    """
    with tempfile.TemporaryDirectory() as tmp_dir:
        workspace = create_workspace(Path(tmp_dir))
        # Register csv-cleaner via internal Python API — fast, no subprocess
        generate_tool_from_prompt(workspace, "Create a tool that cleans CSV files")

        r = _cli(["registry", "info", "csv-cleaner"], workspace, 30)
        assert r.returncode == 0
        assert "csv-cleaner" in r.stdout.lower()
        assert "0.1.0" in r.stdout.lower()
