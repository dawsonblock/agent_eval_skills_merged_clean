#!/usr/bin/env python3
"""E2E script for local-file-hasher proof path."""
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
    """Run the full local-file-hasher e2e lifecycle."""
    print("Starting local-file-hasher e2e lifecycle...")

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
        print("Step 2: Creating local-file-hasher tool...")
        result = run_toolforge(
            [
                "new",
                "tool",
                "--from-prompt",
                "Create a tool that computes SHA256 checksums of local files",
            ],
            cwd=tmp_path,
            timeout=120,
        )
        print(f"New tool stdout: {result.stdout}")

        tool_dir = tmp_path / "tools" / "generated" / "local-file-hasher"
        assert_file_exists(tool_dir / "toolforge.yaml")
        assert_file_exists(tool_dir / "examples" / "sample.txt")

        # 3) generate mcp/skill/eval
        print("Step 3: Generating MCP...")
        result = run_toolforge(
            ["generate", "mcp", "local-file-hasher"],
            cwd=tmp_path,
            timeout=30,
        )
        print("Step 4: Generating skill...")
        result = run_toolforge(
            ["generate", "skill", "local-file-hasher"],
            cwd=tmp_path,
            timeout=30,
        )
        print("Step 5: Generating eval...")
        result = run_toolforge(
            ["generate", "eval", "local-file-hasher"],
            cwd=tmp_path,
            timeout=30,
        )

        # 4) validate
        print("Step 6: Validating...")
        result = run_toolforge(
            ["validate", "local-file-hasher"], cwd=tmp_path, timeout=30
        )

        # 5) run success
        print("Step 7: Running success case...")
        result = run_toolforge(
            [
                "run",
                "local-file-hasher",
                "--input",
                "file_path=examples/sample.txt",
            ],
            cwd=tmp_path,
            timeout=30,
        )
        # Check that output contains algorithm or hash
        assert_contains(
            result.stdout + result.stderr,
            "sha256",
            "Expected hash output to contain sha256",
        )

        # 6) run safety boundary
        print("Step 8: Running safety boundary test...")
        result = run_toolforge(
            [
                "run",
                "local-file-hasher",
                "--input",
                "file_path=../../../etc/passwd",
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
            ["eval", "local-file-hasher"], cwd=tmp_path, timeout=60
        )

        # 8) package
        print("Step 10: Packaging...")
        result = run_toolforge(
            ["package", "local-file-hasher"], cwd=tmp_path, timeout=30
        )

        dist_zip = tmp_path / "dist" / "local-file-hasher-0.1.0.zip"
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
        metadata = registry["local-file-hasher"]["metadata"]
        assert metadata["status"] == "packaged"
        assert metadata["last_run_type"] == "safety_test"
        assert metadata["operational_last_run_success"] is True
        assert metadata["eval_score"] is not None

        print("\n✓ All E2E steps passed.")

        # Check for leaked processes
        assert_no_leaked_processes()

    print("Local file hasher e2e lifecycle completed successfully!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
