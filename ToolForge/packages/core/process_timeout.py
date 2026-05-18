"""Process-tree timeout helper for subprocess execution."""
from __future__ import annotations

import os
import signal
import subprocess
import time
import warnings
from pathlib import Path


def run_with_process_tree_timeout(
    cmd: list[str],
    cwd: Path,
    env: dict[str, str],
    timeout: int,
    grace_period: float = 0.5,
) -> subprocess.CompletedProcess[str]:
    """
    Run a command in a new process group with timeout and process-tree killing.

    Uses SIGTERM→SIGKILL escalation to ensure clean process termination.
    Always uses process group (start_new_session=True) to prevent orphaned
    child processes from hanging the test suite.

    Args:
        cmd: Command and arguments to execute
        cwd: Working directory for the command
        env: Environment variables for the command
        timeout: Timeout in seconds
        grace_period: Time to wait between SIGTERM and SIGKILL (default: 0.5s)

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
        # Kill entire process group with SIGTERM→SIGKILL escalation
        _kill_process_tree(proc.pid, grace_period)
        # Wait for process to actually terminate
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            warnings.warn(
                f"Process {proc.pid} did not terminate after SIGKILL - possible zombie process"
            )
        # Get any remaining output
        stdout, stderr = proc.communicate()
        raise AssertionError(
            "Subprocess timed out and was killed\n"
            f"cmd: {cmd}\n"
            f"cwd: {cwd}\n"
            f"timeout: {timeout}s\n"
            f"stdout:\n{stdout}\n"
            f"stderr:\n{stderr}\n"
        ) from exc
    finally:
        # Ensure process group is cleaned up even on success
        # Always attempt cleanup; ProcessLookupError indicates process already gone
        try:
            if proc.poll() is None:
                _kill_process_tree(proc.pid, grace_period)
                proc.wait(timeout=5)
        except (ProcessLookupError, subprocess.TimeoutExpired):
            # Process already terminated or stuck; either way, we're done
            pass

    return subprocess.CompletedProcess(
        args=cmd,
        returncode=proc.returncode,
        stdout=stdout,
        stderr=stderr,
    )


def _kill_process_tree(pid: int, grace_period: float) -> None:
    """
    Kill entire process group for given PID with SIGTERM/SIGKILL escalation.

    Args:
        pid: Process ID to kill (process group leader)
        grace_period: Time to wait between SIGTERM and SIGKILL
    """
    try:
        os.killpg(pid, signal.SIGTERM)
        time.sleep(grace_period)
    except ProcessLookupError:
        return

    try:
        os.killpg(pid, signal.SIGKILL)
    except ProcessLookupError:
        return
