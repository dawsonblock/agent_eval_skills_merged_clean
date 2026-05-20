"""Child-script regression for validate failure when tests/ is missing."""
from __future__ import annotations

import sys
from pathlib import Path

from tests.e2e_scripts._lifecycle import (
    generate_eval,
    generate_mcp,
    generate_skill,
    generate_tool_from_prompt,
    init_workspace,
)
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

    # Build lifecycle artifacts via internal helpers to avoid repeated nested
    # CLI subprocesses. We only subprocess the validate command under test.
    init_workspace(workspace)
    generate_tool_from_prompt(workspace, PROMPT)
    generate_mcp(workspace, "csv-cleaner")
    generate_skill(workspace, "csv-cleaner")
    generate_eval(workspace, "csv-cleaner")

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
