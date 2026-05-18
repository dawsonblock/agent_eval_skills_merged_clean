"""E2E script runner with process isolation and timeout handling."""
from __future__ import annotations

import os
import subprocess
import sys
import zipfile
from pathlib import Path

from tests.e2e_scripts._timeout import run_with_process_tree_timeout


def find_toolforge_root() -> Path:
    """Find the ToolForge repository root directory."""
    current = Path(__file__).parent.parent.parent
    while current != current.parent:
        if (current / "pyproject.toml").exists():
            return current
        current = current.parent
    return Path.cwd()


def build_clean_env() -> dict[str, str]:
    """Build a clean environment for subprocess execution."""
    env = os.environ.copy()

    # Strip pytest-related env vars
    for key in (
        "PYTEST_CURRENT_TEST",
        "PYTEST_VERSION",
        "PYTEST_ADDOPTS",
        "PYTEST_PLUGINS",
        "COVERAGE_PROCESS_START",
    ):
        env.pop(key, None)

    # Set isolation flags
    env["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PYTHONUNBUFFERED"] = "1"

    # Set PYTHONPATH explicitly
    root = find_toolforge_root()
    paths = [str(root), str(root / "apps" / "cli")]
    existing_pythonpath = env.get("PYTHONPATH", "")
    if existing_pythonpath:
        paths.append(existing_pythonpath)
    env["PYTHONPATH"] = os.pathsep.join(paths)

    return env


def run_toolforge(
    args: list[str],
    cwd: Path,
    timeout: int = 60,
    check: bool = True,
) -> subprocess.CompletedProcess:
    """
    Run toolforge command with process isolation and timeout.

    Args:
        args: Command arguments to pass to toolforge
        cwd: Working directory for the command
        timeout: Timeout in seconds
        check: If True, raise AssertionError on non-zero returncode

    Returns:
        CompletedProcess with stdout and stderr
    """
    env = build_clean_env()
    cmd = [sys.executable, "-m", "apps.cli.toolforge_cli.main", *args]

    result = run_with_process_tree_timeout(cmd, cwd, env, timeout)

    if check and result.returncode != 0:
        raise AssertionError(
            f"Command failed with return code {result.returncode}: {cmd}\n"
            f"cwd={cwd}\n"
            f"stdout:\n{result.stdout}\n"
            f"stderr:\n{result.stderr}"
        )

    return result


def assert_contains(text: str, substring: str, message: str = "") -> None:
    """Assert that text contains substring."""
    if substring not in text:
        raise AssertionError(f"{message}\nExpected '{substring}' in:\n{text}")


def assert_file_exists(path: Path) -> None:
    """Assert that a file exists."""
    if not path.exists():
        raise AssertionError(f"File does not exist: {path}")


def assert_zip_contains(zip_path: Path, expected_files: list[str]) -> None:
    """Assert that zip file contains expected files."""
    with zipfile.ZipFile(zip_path) as zf:
        names = set(zf.namelist())
        for expected in expected_files:
            if expected not in names:
                raise AssertionError(
                    f"Zip {zip_path} missing expected file: {expected}"
                )


def assert_zip_excludes(zip_path: Path, excluded_patterns: list[str]) -> None:
    """Assert that zip file excludes files matching patterns."""
    with zipfile.ZipFile(zip_path) as zf:
        names = zf.namelist()
        for pattern in excluded_patterns:
            for name in names:
                if pattern in name:
                    raise AssertionError(
                        f"Zip {zip_path} should exclude pattern "
                        f"'{pattern}' but found: {name}"
                    )


def assert_no_leaked_processes() -> None:
    """Assert no ToolForge-related processes are still running."""
    try:
        # Use ps to check for leaked processes
        result = subprocess.run(
            ["ps", "aux"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        leaked = []
        for line in result.stdout.splitlines():
            line_lower = line.lower()
            # Only flag actual ToolForge subprocess processes
            # Exclude: mypy, pytest, shell commands, ps itself, grep
            if "apps.cli.toolforge_cli.main" in line_lower:
                # Skip if it's mypy, pytest, or the parent shell
                if "mypy" not in line_lower and "pytest" not in line_lower:
                    # Also skip if it's a grep command checking for processes
                    if "grep" not in line_lower:
                        leaked.append(line)

        if leaked:
            raise AssertionError(
                "Found leaked ToolForge processes:\n" + "\n".join(leaked)
            )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        # ps command not available or timed out - skip check
        pass
