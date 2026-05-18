#!/usr/bin/env python3
"""Process-tree timeout wrapper for ToolForge demo commands."""
from __future__ import annotations

import os
import sys
from pathlib import Path

# Add ToolForge to path for imports
repo_root = Path(__file__).parent.parent / "ToolForge"
sys.path.insert(0, str(repo_root))

from tests.e2e_scripts._timeout import (  # noqa: E402
    run_with_process_tree_timeout,
)


def main() -> int:
    """Run command with timeout and process-group killing."""
    if len(sys.argv) < 2:
        msg = "Usage: run_with_timeout.py --timeout SECONDS -- command args..."
        print(msg, file=sys.stderr)
        return 1

    # Parse arguments
    try:
        timeout_idx = sys.argv.index("--timeout")
        timeout = int(sys.argv[timeout_idx + 1])
        cmd_start = timeout_idx + 2
    except (ValueError, IndexError):
        msg = "Error: --timeout argument required with integer value"
        print(msg, file=sys.stderr)
        return 1

    cmd = sys.argv[cmd_start:]

    # Run command in new process group using consolidated helper
    try:
        result = run_with_process_tree_timeout(
            cmd,
            cwd=Path.cwd(),
            env=os.environ.copy(),
            timeout=timeout,
        )
        sys.stdout.write(result.stdout)
        sys.stderr.write(result.stderr)
        return result.returncode
    except AssertionError as exc:
        # Timeout occurred - consolidated helper already killed process
        sys.stdout.write(str(exc))
        return 124  # timeout exit code


if __name__ == "__main__":
    sys.exit(main())
