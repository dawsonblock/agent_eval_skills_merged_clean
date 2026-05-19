"""Test registry CLI commands exit reliably without hanging."""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path

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
    """Test registry list command exits without hanging."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)

        r = _cli(["init", str(tmp_path)], tmp_path, 30)
        assert r.returncode == 0

        # Generate csv-cleaner so the registry has an entry to list
        r = _cli(
            ["new", "tool", "--from-prompt", "Create a tool that cleans CSV files"],
            tmp_path,
            120,
        )
        assert r.returncode == 0

        r = _cli(["registry", "list"], tmp_path, 30)
        assert r.returncode == 0
        assert "csv-cleaner" in r.stdout.lower()


def test_registry_info_exits_cleanly() -> None:
    """Test registry info command exits without hanging."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)

        r = _cli(["init", str(tmp_path)], tmp_path, 30)
        assert r.returncode == 0

        r = _cli(
            ["new", "tool", "--from-prompt", "Create a tool that cleans CSV files"],
            tmp_path,
            120,
        )
        assert r.returncode == 0

        r = _cli(["registry", "info", "csv-cleaner"], tmp_path, 30)
        assert r.returncode == 0
        assert "csv-cleaner" in r.stdout.lower()
        assert "v0.1.0" in r.stdout.lower()
