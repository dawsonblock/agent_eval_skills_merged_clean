"""Process-tree killing helper for pytest e2e wrappers."""
from __future__ import annotations

import os
import signal
import subprocess
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
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
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
            try:
                os.killpg(proc.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
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
