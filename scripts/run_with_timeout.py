#!/usr/bin/env python3
"""Process-tree timeout wrapper for ToolForge demo commands."""
from __future__ import annotations

import os
import signal
import subprocess
import sys


def main() -> int:
    """Run command with timeout and process-group killing."""
    if len(sys.argv) < 2:
        print("Usage: run_with_timeout.py --timeout SECONDS -- command args...", file=sys.stderr)
        return 1

    # Parse arguments
    try:
        timeout_idx = sys.argv.index("--timeout")
        timeout = int(sys.argv[timeout_idx + 1])
        cmd_start = timeout_idx + 2
    except (ValueError, IndexError):
        print("Error: --timeout argument required with integer value", file=sys.stderr)
        return 1

    cmd = sys.argv[cmd_start:]

    # Run command in new process group
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        start_new_session=True,
    )

    try:
        stdout, stderr = proc.communicate(timeout=timeout)
        sys.stdout.write(stdout)
        sys.stderr.write(stderr)
        return proc.returncode
    except subprocess.TimeoutExpired:
        # Kill entire process group
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        # Get any remaining output
        stdout, stderr = proc.communicate()
        sys.stdout.write(stdout)
        sys.stderr.write(stderr)
        return 124  # timeout exit code


if __name__ == "__main__":
    sys.exit(main())
