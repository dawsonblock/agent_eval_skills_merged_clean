"""Process-tree killing helper for pytest e2e wrappers."""
from __future__ import annotations

import subprocess
from pathlib import Path

from tests.e2e_scripts._timeout import run_with_process_tree_timeout


def run_process_tree(
    cmd: list[str],
    cwd: Path,
    env: dict[str, str],
    timeout: int = 180,
) -> subprocess.CompletedProcess[str]:
    """
    Run a command in a new process group with timeout and process-tree killing.

    If the command times out, the entire process group is killed to prevent
    orphaned child processes from hanging the test suite.

    Args:
        cmd: Command and arguments to execute
        cwd: Working directory for the command
        env: Environment variables for the command
        timeout: Timeout in seconds (default: 180)

    Returns:
        CompletedProcess with stdout, stderr, and returncode

    Raises:
        AssertionError: If the command times out or returns non-zero exit code
    """
    return run_with_process_tree_timeout(cmd, cwd, env, timeout)


def collect_matching_processes(patterns: list[str]) -> list[str]:
    """Collect processes matching given patterns using ps."""
    try:
        result = subprocess.run(
            ["ps", "aux"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        matched = []
        for line in result.stdout.splitlines():
            line_lower = line.lower()
            if any(pattern.lower() in line_lower for pattern in patterns):
                # Skip the ps command itself
                if "ps aux" not in line_lower:
                    matched.append(line)
        return matched
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return []


def assert_no_toolforge_children() -> None:
    """Assert no ToolForge-related processes are still running."""
    leaked = collect_matching_processes([
        "apps.cli.toolforge_cli.main",
        "toolforge",
        "tools/generated/",
    ])
    if leaked:
        raise AssertionError(
            "Found leaked ToolForge processes:\n" + "\n".join(leaked)
        )
