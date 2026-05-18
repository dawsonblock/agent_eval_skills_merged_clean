#!/usr/bin/env python3
"""E2E script for csv-cleaner proof path - runs in isolated process."""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

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

        # 1) init
        print("Step 1: Initializing workspace...")
        result = run_toolforge(
            ["init", str(tmp_path)], cwd=tmp_path, timeout=30
        )
        print(f"Init stdout: {result.stdout}")

        # 2) new tool from prompt
        print("Step 2: Creating csv-cleaner tool...")
        result = run_toolforge(
            [
                "new",
                "tool",
                "--from-prompt",
                "Create a tool that cleans CSV files",
            ],
            cwd=tmp_path,
            timeout=120,
        )
        print(f"New tool stdout: {result.stdout}")

        tool_dir = tmp_path / "tools" / "generated" / "csv-cleaner"
        assert_file_exists(tool_dir / "toolforge.yaml")
        assert_file_exists(tool_dir / "tool.py")
        assert_file_exists(tool_dir / "examples" / "input.csv")

        # 3) generate mcp/skill/eval
        print("Step 3: Generating MCP...")
        result = run_toolforge(
            ["generate", "mcp", "csv-cleaner"], cwd=tmp_path, timeout=30
        )
        assert_file_exists(tool_dir / "mcp" / "server.py")

        print("Step 4: Generating skill...")
        result = run_toolforge(
            ["generate", "skill", "csv-cleaner"], cwd=tmp_path, timeout=30
        )
        assert_file_exists(tool_dir / "skill" / "SKILL.md")

        print("Step 5: Generating eval...")
        result = run_toolforge(
            ["generate", "eval", "csv-cleaner"], cwd=tmp_path, timeout=30
        )
        assert_file_exists(
            tool_dir / "evals" / "cases" / "case-01-success.json"
        )

        # 4) validate
        print("Step 6: Validating...")
        result = run_toolforge(
            ["validate", "csv-cleaner"], cwd=tmp_path, timeout=30
        )

        # 5) run success
        print("Step 7: Running success case...")
        result = run_toolforge(
            ["run", "csv-cleaner", "--input", "input_path=examples/input.csv"],
            cwd=tmp_path,
            timeout=30,
        )
        print(f"Run stdout: {result.stdout}")
        print(f"Run stderr: {result.stderr}")
        # Check that the output file was created
        assert_file_exists(tool_dir / "outputs" / "cleaned.csv")
        # Check that output contains cleaned_path
        assert_contains(result.stdout, "cleaned_path")

        # 6) run safety boundary
        print("Step 8: Running safety boundary test...")
        result = run_toolforge(
            [
                "run",
                "csv-cleaner",
                "--input",
                "input_path=../../../etc/passwd",
            ],
            cwd=tmp_path,
            timeout=30,
            check=False,
        )
        assert result.returncode != 0
        assert_contains(
            result.stdout + result.stderr, "Path validation failed"
        )

        # 7) eval
        print("Step 9: Running eval...")
        result = run_toolforge(
            ["eval", "csv-cleaner"], cwd=tmp_path, timeout=30
        )

        # 8) package
        print("Step 10: Packaging...")
        result = run_toolforge(
            ["package", "csv-cleaner"], cwd=tmp_path, timeout=30
        )

        dist_zip = tmp_path / "dist" / "csv-cleaner-0.1.0.zip"
        assert_file_exists(dist_zip)

        assert_zip_contains(
            dist_zip, ["toolforge.yaml", "tool.py", "mcp/server.py"]
        )
        assert_zip_contains(dist_zip, ["skill/SKILL.md"])
        assert_zip_contains(dist_zip, ["evals/task_config.json"])
        assert_zip_contains(dist_zip, ["SECURITY.md"])
        assert_zip_excludes(dist_zip, ["__pycache__", ".pyc", ".coverage"])

        # 9) registry values advanced
        print("Step 11: Checking registry...")
        registry_path = tmp_path / "toolforge_registry.json"
        registry = json.loads(registry_path.read_text(encoding="utf-8"))
        metadata = registry["csv-cleaner"]["metadata"]
        assert metadata["mcp_path"]
        assert metadata["skill_path"]
        assert metadata["eval_path"]
        assert metadata["last_validation"]
        assert metadata["last_run"]
        assert metadata["last_run_success"] is False
        assert metadata["last_run_type"] == "safety_test"

        print("\n✓ All E2E steps passed.")

        # Check for leaked processes
        assert_no_leaked_processes()

        assert metadata["operational_last_run_success"] is True
        assert metadata["last_successful_run"]
        assert metadata["last_failed_run"]
        assert metadata["eval_score"] is not None
        assert metadata["package_path"]

    print("CSV cleaner e2e lifecycle completed successfully!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
