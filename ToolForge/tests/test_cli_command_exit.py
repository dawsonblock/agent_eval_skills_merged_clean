"""Focused CLI command exit tests for hang-prone commands."""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

import pytest

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


def test_validate_cli_exit() -> None:
    """Test validate command exits cleanly without hangs."""
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

        # First create a simple tool
        result = run_process_tree(
            [
                sys.executable,
                "-m",
                "apps.cli.toolforge_cli.main",
                "new",
                "tool",
                "--from-prompt",
                "Create a simple tool",
                "--slug",
                "simple-tool",
            ],
            cwd=tmp_path,
            env=env,
            timeout=60,
        )
        assert result.returncode == 0

        # Test validate command - may fail if tool generation didn't produce a complete tool
        # but should not hang
        result = run_process_tree(
            [sys.executable, "-m", "apps.cli.toolforge_cli.main", "validate", "simple-tool"],
            cwd=tmp_path,
            env=env,
            timeout=60,
        )
        # Exit code may be 0 or non-zero depending on validation results
        # The important thing is it doesn't hang and returns a valid exit code
        assert result.returncode is not None


def test_run_cli_exit() -> None:
    """Test run command exits cleanly without hangs."""
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

        # Create a simple tool
        result = run_process_tree(
            [
                sys.executable,
                "-m",
                "apps.cli.toolforge_cli.main",
                "new",
                "tool",
                "--from-prompt",
                "Create a tool that echoes text",
                "--slug",
                "echo-tool",
            ],
            cwd=tmp_path,
            env=env,
            timeout=60,
        )
        assert result.returncode == 0

        # Test run command with a simple input
        result = run_process_tree(
            [
                sys.executable,
                "-m",
                "apps.cli.toolforge_cli.main",
                "run",
                "echo-tool",
                "--input",
                "text=hello",
            ],
            cwd=tmp_path,
            env=env,
            timeout=30,
        )
        # May fail if tool generation didn't produce a working tool,
        # but should not hang and should return a valid exit code
        assert result.returncode is not None


def test_csv_cleaner_command_exit() -> None:
    """Test csv-cleaner specific command exits cleanly without hangs."""
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

        # Generate csv-cleaner tool
        result = run_process_tree(
            [
                sys.executable,
                "-m",
                "apps.cli.toolforge_cli.main",
                "new",
                "tool",
                "--from-prompt",
                "Create a tool that cleans CSV files",
            ],
            cwd=tmp_path,
            env=env,
            timeout=120,
        )
        assert result.returncode == 0

        # Test validate command
        result = run_process_tree(
            [sys.executable, "-m", "apps.cli.toolforge_cli.main", "validate", "csv-cleaner"],
            cwd=tmp_path,
            env=env,
            timeout=60,
        )
        # May fail if validation finds issues, but should not hang
        assert result.returncode is not None

        # Test package command
        result = run_process_tree(
            [sys.executable, "-m", "apps.cli.toolforge_cli.main", "package", "csv-cleaner"],
            cwd=tmp_path,
            env=env,
            timeout=60,
        )
        # May fail if tool generation didn't produce a complete tool,
        # but should not hang and should return a valid exit code
        assert result.returncode is not None


def test_json_schema_validator_command_exit() -> None:
    """Test json-schema-validator specific command exits cleanly without hangs."""
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

        # Generate json-schema-validator tool
        result = run_process_tree(
            [
                sys.executable,
                "-m",
                "apps.cli.toolforge_cli.main",
                "new",
                "tool",
                "--from-prompt",
                "Create a tool that validates JSON files against a schema",
            ],
            cwd=tmp_path,
            env=env,
            timeout=120,
        )
        assert result.returncode == 0

        # Test package command
        result = run_process_tree(
            [sys.executable, "-m", "apps.cli.toolforge_cli.main", "package", "json-schema-validator"],
            cwd=tmp_path,
            env=env,
            timeout=60,
        )
        # May fail if tool generation didn't produce a complete tool,
        # but should not hang and should return a valid exit code
        assert result.returncode is not None


@pytest.mark.parametrize(
    "tool_slug,tool_prompt",
    [
        ("csv-cleaner", "Create a tool that cleans CSV files"),
        ("json-schema-validator", "Create a tool that validates JSON files against a schema"),
        ("local-file-hasher", "Create a tool that computes SHA256 hashes for local files"),
    ],
)
def test_eval_command_exit(tool_slug: str, tool_prompt: str) -> None:
    """Test eval command exits cleanly without hangs for various tools."""
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

        # Generate tool
        result = run_process_tree(
            [
                sys.executable,
                "-m",
                "apps.cli.toolforge_cli.main",
                "new",
                "tool",
                "--from-prompt",
                tool_prompt,
            ],
            cwd=tmp_path,
            env=env,
            timeout=120,
        )
        assert result.returncode == 0

        # Test eval command with process-tree timeout
        result = run_process_tree(
            [sys.executable, "-m", "apps.cli.toolforge_cli.main", "eval", tool_slug],
            cwd=tmp_path,
            env=env,
            timeout=60,
        )
        # May fail if eval cases fail or tool generation incomplete,
        # but should not hang and should return a valid exit code
        assert result.returncode is not None
