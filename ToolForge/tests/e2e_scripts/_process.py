"""Process-tree killing helper for pytest e2e wrappers."""
from __future__ import annotations

import os
import signal
import subprocess
import time
from pathlib import Path


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
    proc = subprocess.Popen(
        cmd,
        cwd=cwd,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        start_new_session=True,
    )

    try:
        stdout, stderr = proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired as exc:
        # Kill entire process group
        kill_process_tree(proc.pid)
        time.sleep(0.25)
        # Wait for process to actually terminate
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            pass
        # Get any remaining output
        stdout, stderr = proc.communicate()
        raise AssertionError(
            "E2E subprocess timed out and was killed\n"
            f"cmd: {cmd}\n"
            f"cwd: {cwd}\n"
            f"timeout: {timeout}\n"
            f"stdout:\n{stdout}\n"
            f"stderr:\n{stderr}\n"
        ) from exc
    finally:
        # Ensure process group is cleaned up even on success
        if proc.poll() is None:
            kill_process_tree(proc.pid)
            time.sleep(0.25)
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                pass

    return subprocess.CompletedProcess(
        args=cmd,
        returncode=proc.returncode,
        stdout=stdout,
        stderr=stderr,
    )


def kill_process_tree(pid: int) -> None:
    """Kill entire process group for given PID."""
    try:
        os.killpg(pid, signal.SIGKILL)
    except ProcessLookupError:
        return


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
