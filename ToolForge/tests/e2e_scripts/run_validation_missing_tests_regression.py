"""Child-script regression for validate failure when tests/ is missing."""
from __future__ import annotations

import sys
from pathlib import Path

from tests.e2e_scripts._runner import run_toolforge


PROMPT = "Create a tool that cleans CSV files"


def _combined(stdout: str, stderr: str) -> str:
    return (stdout or "") + ("\n" + stderr if stderr else "")


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: run_validation_missing_tests_regression.py <workspace>", file=sys.stderr)
        return 2

    workspace = Path(sys.argv[1]).resolve()
    workspace.mkdir(parents=True, exist_ok=True)

    steps = [
        (["init", str(workspace)], 0),
        (["new", "tool", "--from-prompt", PROMPT], 0),
        (["generate", "mcp", "csv-cleaner"], 0),
        (["generate", "skill", "csv-cleaner"], 0),
        (["generate", "eval", "csv-cleaner"], 0),
    ]

    for cmd, expected_rc in steps:
        result = run_toolforge(cmd, cwd=workspace, check=False)
        if result.returncode != expected_rc:
            print(_combined(result.stdout, result.stderr), file=sys.stderr)
            return 1

    tool_dir = workspace / "tools" / "generated" / "csv-cleaner"
    (tool_dir / "tests").rename(tool_dir / "tests_backup")

    validate = run_toolforge(["validate", "csv-cleaner"], cwd=workspace, check=False)
    output = _combined(validate.stdout, validate.stderr)
    print(output)
    if validate.returncode != 1:
        return 1
    if "Missing tests/ directory" not in output:
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
