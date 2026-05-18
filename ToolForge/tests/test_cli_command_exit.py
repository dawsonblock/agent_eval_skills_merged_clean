"""Focused CLI command exit tests for hang-prone commands."""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

from tests.e2e_scripts._process import run_process_tree


def build_clean_env(root: Path) -> dict[str, str]:
    """Build clean environment for subprocess execution."""
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
    existing_pythonpath = env.get("PYTHONPATH", "")
    if existing_pythonpath:
        paths.append(existing_pythonpath)
    env["PYTHONPATH"] = os.pathsep.join(paths)

    return env


def test_registry_cli_exit() -> None:
    """Test registry commands exit cleanly without hangs."""
    root = Path(__file__).parent.parent
    env = build_clean_env(root)

    # Test registry list
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        result = run_process_tree(
            [sys.executable, "-m", "apps.cli.toolforge_cli.main", "init", str(tmp_path)],
            cwd=root,
            env=env,
            timeout=30,
        )
        assert result.returncode == 0

        result = run_process_tree(
            [sys.executable, "-m", "apps.cli.toolforge_cli.main", "registry", "list"],
            cwd=tmp_path,
            env=env,
            timeout=30,
        )
        assert result.returncode == 0
        assert "No tools registered" in result.stdout or "Registered Tools" in result.stdout

        # Test registry info (should fail for non-existent tool)
        result = run_process_tree(
            [sys.executable, "-m", "apps.cli.toolforge_cli.main", "registry", "info", "csv-cleaner"],
            cwd=tmp_path,
            env=env,
            timeout=30,
        )
        assert result.returncode != 0


def test_eval_cli_exit() -> None:
    """Test eval command exits cleanly without hangs."""
    root = Path(__file__).parent.parent
    env = build_clean_env(root)

    # Test eval command (should fail for non-existent tool)
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        result = run_process_tree(
            [sys.executable, "-m", "apps.cli.toolforge_cli.main", "init", str(tmp_path)],
            cwd=root,
            env=env,
            timeout=30,
        )
        assert result.returncode == 0

        result = run_process_tree(
            [sys.executable, "-m", "apps.cli.toolforge_cli.main", "eval", "csv-cleaner"],
            cwd=tmp_path,
            env=env,
            timeout=30,
        )
        assert result.returncode != 0


def test_new_tool_cli_exit() -> None:
    """Test new tool command exits cleanly without hangs."""
    root = Path(__file__).parent.parent
    env = build_clean_env(root)

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        result = run_process_tree(
            [sys.executable, "-m", "apps.cli.toolforge_cli.main", "init", str(tmp_path)],
            cwd=root,
            env=env,
            timeout=30,
        )
        assert result.returncode == 0

        # Test new tool command (known to hang in some cases)
        result = run_process_tree(
            [
                sys.executable,
                "-m",
                "apps.cli.toolforge_cli.main",
                "new",
                "tool",
                "--from-prompt",
                "Create a tool that computes SHA256 hashes for local files",
            ],
            cwd=tmp_path,
            env=env,
            timeout=60,
        )
        assert result.returncode == 0
