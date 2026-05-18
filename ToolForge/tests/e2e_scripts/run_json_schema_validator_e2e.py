#!/usr/bin/env python3
"""E2E script for json-schema-validator proof path."""
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
    assert_zip_contains,
    assert_zip_excludes,
    run_toolforge,
)


def main() -> int:
    """Run the full json-schema-validator e2e lifecycle."""
    print("Starting json-schema-validator e2e lifecycle...")

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
        print("Step 2: Creating json-schema-validator tool...")
        result = run_toolforge(
            [
                "new",
                "tool",
                "--from-prompt",
                "Create a tool that validates JSON files against a schema",
            ],
            cwd=tmp_path,
            timeout=120,
        )
        print(f"New tool stdout: {result.stdout}")

        tool_dir = tmp_path / "tools" / "generated" / "json-schema-validator"
        assert_file_exists(tool_dir / "toolforge.yaml")
        assert_file_exists(tool_dir / "examples" / "schema.json")
        assert_file_exists(tool_dir / "examples" / "data_valid.json")

        # 3) generate mcp/skill/eval
        print("Step 3: Generating MCP...")
        result = run_toolforge(
            ["generate", "mcp", "json-schema-validator"],
            cwd=tmp_path,
            timeout=30,
        )
        print("Step 4: Generating skill...")
        result = run_toolforge(
            ["generate", "skill", "json-schema-validator"],
            cwd=tmp_path,
            timeout=30,
        )
        print("Step 5: Generating eval...")
        result = run_toolforge(
            ["generate", "eval", "json-schema-validator"],
            cwd=tmp_path,
            timeout=30,
        )

        # 4) validate
        print("Step 6: Validating...")
        result = run_toolforge(
            ["validate", "json-schema-validator"], cwd=tmp_path, timeout=30
        )

        # 5) run success
        print("Step 7: Running success case...")
        result = run_toolforge(
            [
                "run",
                "json-schema-validator",
                "--input",
                "data_path=examples/data_valid.json",
                "--input",
                "schema_path=examples/schema.json",
            ],
            cwd=tmp_path,
            timeout=30,
        )
        # Check that output contains valid: true
        assert_contains(result.stdout, '"valid": true')

        # 6) run safety boundary
        print("Step 8: Running safety boundary test...")
        result = run_toolforge(
            [
                "run",
                "json-schema-validator",
                "--input",
                "data_path=../../../etc/passwd",
                "--input",
                "schema_path=examples/schema.json",
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
            ["eval", "json-schema-validator"], cwd=tmp_path, timeout=60
        )

        # 8) package
        print("Step 10: Packaging...")
        result = run_toolforge(
            ["package", "json-schema-validator"], cwd=tmp_path, timeout=30
        )

        dist_zip = tmp_path / "dist" / "json-schema-validator-0.1.0.zip"
        assert_file_exists(dist_zip)

        assert_zip_contains(
            dist_zip, ["toolforge.yaml", "tool.py", "skill/SKILL.md"]
        )
        assert_zip_contains(dist_zip, ["evals/task_config.json"])
        assert_zip_contains(dist_zip, ["SECURITY.md"])
        assert_zip_excludes(dist_zip, ["outputs/"])

        # 9) registry values
        print("Step 11: Checking registry...")
        registry_path = tmp_path / "toolforge_registry.json"
        registry = json.loads(registry_path.read_text(encoding="utf-8"))
        metadata = registry["json-schema-validator"]["metadata"]
        assert metadata["status"] == "packaged"
        assert metadata["last_run_type"] == "safety_test"
        assert metadata["operational_last_run_success"] is True
        assert metadata["eval_score"] is not None

    print("JSON schema validator e2e lifecycle completed successfully!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
