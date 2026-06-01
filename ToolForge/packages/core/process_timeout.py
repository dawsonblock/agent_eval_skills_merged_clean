"""Process-tree timeout helper for subprocess execution."""

from __future__ import annotations

import os
import signal
import subprocess
import time
import warnings
from pathlib import Path


class ProcessTimeoutError(Exception):
    """Raised when a subprocess times out and is killed."""

    pass


def run_with_process_tree_timeout(
    cmd: list[str],
    cwd: Path,
    env: dict[str, str],
    timeout: float,
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
        ProcessTimeoutError: If the command times out
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
        # Drain remaining output with a hard ceiling so we never block
        # indefinitely here (e.g. zombie process or grandchild that escaped
        # the process-group kill still holding a pipe open).
        try:
            stdout, stderr = proc.communicate(timeout=10)
        except subprocess.TimeoutExpired:
            # Truly stuck — close the pipes ourselves so reads unblock, then
            # fall back to empty strings for the diagnostic message.
            if proc.stdout:
                proc.stdout.close()
            if proc.stderr:
                proc.stderr.close()
            stdout, stderr = "", ""
        raise ProcessTimeoutError(
            "Subprocess timed out and was killed\n"
            f"cmd: {cmd}\n"
            f"cwd: {cwd}\n"
            f"timeout: {timeout}s\n"
            f"stdout:\n{stdout}\n"
            f"stderr:\n{stderr}\n"
        ) from exc

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
