#!/usr/bin/env python3
"""E2E script for csv-cleaner proof path - runs in isolated process."""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from tests.e2e_scripts._lifecycle import (  # noqa: E402
    assert_registry_packaged,
    create_workspace,
    generate_eval,
    generate_mcp,
    generate_skill,
    generate_tool_from_prompt,
    package_tool,
    validate_tool,
)
from tests.e2e_scripts._runner import (  # noqa: E402
    assert_contains,
    assert_file_exists,
    assert_no_leaked_processes,
    assert_zip_contains,
    assert_zip_excludes,
    run_toolforge,
)


def main() -> int:
    """Run the full csv-cleaner e2e lifecycle."""
    print("Starting csv-cleaner e2e lifecycle...")

    # Create temporary workspace
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)

        # 1) init - use internal helper
        print("Step 1: Initializing workspace...")
        workspace = create_workspace(tmp_path)
        print(f"Workspace created at: {workspace}")

        # 2) new tool from prompt - use internal helper
        print("Step 2: Creating csv-cleaner tool...")
        spec = generate_tool_from_prompt(
            workspace, "Create a tool that cleans CSV files", slug="csv-cleaner"
        )
        print(f"Tool spec created: {spec.slug}")

        tool_dir = workspace / "tools" / "generated" / "csv-cleaner"
        assert_file_exists(tool_dir / "toolforge.yaml")
        assert_file_exists(tool_dir / "tool.py")
        assert_file_exists(tool_dir / "examples" / "input.csv")

        # 3) generate mcp/skill/eval - use internal helpers
        print("Step 3: Generating MCP...")
        generate_mcp(workspace, "csv-cleaner")
        assert_file_exists(tool_dir / "mcp" / "server.py")

        print("Step 4: Generating skill...")
        generate_skill(workspace, "csv-cleaner")
        assert_file_exists(tool_dir / "skill" / "SKILL.md")

        print("Step 5: Generating eval...")
        generate_eval(workspace, "csv-cleaner")
        assert_file_exists(
            tool_dir / "evals" / "cases" / "case-01-success.json"
        )

        # 4) validate - use internal helper
        print("Step 6: Validating...")
        validate_tool(workspace, "csv-cleaner")

        # 5) run success - CLI subprocess for black-box check
        print("Step 7: Running success case...")
        result = run_toolforge(
            ["run", "csv-cleaner", "--input", "input_path=examples/input.csv"],
            cwd=workspace,
            timeout=30,
        )
        print(f"Run stdout: {result.stdout}")
        print(f"Run stderr: {result.stderr}")
        # Check that the output file was created
        assert_file_exists(tool_dir / "outputs" / "cleaned.csv")
        # Check that output contains cleaned_path
        assert_contains(result.stdout, "cleaned_path")

        # 6) run safety boundary - CLI subprocess for black-box check
        print("Step 8: Running safety boundary test...")
        result = run_toolforge(
            [
                "run",
                "csv-cleaner",
                "--input",
                "input_path=../../../etc/passwd",
            ],
            cwd=workspace,
            timeout=30,
            check=False,
        )
        assert result.returncode != 0
        assert_contains(
            result.stdout + result.stderr, "Path validation failed"
        )

        # 7) eval - CLI subprocess for black-box check
        print("Step 9: Running eval...")
        result = run_toolforge(
            ["eval", "csv-cleaner"], cwd=workspace, timeout=30
        )

        # 8) package - use internal helper
        print("Step 10: Packaging...")
        package_path = package_tool(workspace, "csv-cleaner")
        assert_file_exists(package_path)

        assert_zip_contains(
            package_path, ["toolforge.yaml", "tool.py", "mcp/server.py"]
        )
        assert_zip_contains(package_path, ["skill/SKILL.md"])
        assert_zip_contains(package_path, ["evals/task_config.json"])
        assert_zip_contains(package_path, ["SECURITY.md"])
        assert_zip_excludes(package_path, ["__pycache__", ".pyc", ".coverage"])

        # 9) registry check - use internal helper
        print("Step 11: Checking registry...")
        assert_registry_packaged(workspace, "csv-cleaner")

        print("\n✓ All E2E steps passed.")

        # Check for leaked processes
        assert_no_leaked_processes()

    print("CSV cleaner e2e lifecycle completed successfully!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
