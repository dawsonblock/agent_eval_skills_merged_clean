#!/usr/bin/env python3
"""E2E script for local-file-hasher proof path."""
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
    assert_file_exists,
    assert_no_leaked_processes,
    assert_zip_contains,
    assert_zip_excludes,
)


def main() -> int:
    """Run the full local-file-hasher e2e lifecycle."""
    print("Starting local-file-hasher e2e lifecycle...")

    # Create temporary workspace
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)

        # 1) init - use internal helper
        print("Step 1: Initializing workspace...")
        workspace = create_workspace(tmp_path)
        print(f"Workspace created at: {workspace}")

        # 2) new tool from prompt - use internal helper
        print("Step 2: Creating local-file-hasher tool...")
        spec = generate_tool_from_prompt(
            workspace,
            "Create a tool that computes SHA256 checksums of local files",
            slug="local-file-hasher",
        )
        print(f"Tool spec created: {spec.slug}")

        tool_dir = workspace / "tools" / "generated" / "local-file-hasher"
        assert_file_exists(tool_dir / "toolforge.yaml")
        assert_file_exists(tool_dir / "examples" / "sample.txt")

        # 3) generate mcp/skill/eval - use internal helpers
        print("Step 3: Generating MCP...")
        generate_mcp(workspace, "local-file-hasher")

        print("Step 4: Generating skill...")
        generate_skill(workspace, "local-file-hasher")

        print("Step 5: Generating eval...")
        generate_eval(workspace, "local-file-hasher")

        # 4) validate - use internal helper
        print("Step 6: Validating...")
        validate_tool(workspace, "local-file-hasher")

        # 5) eval - use internal helper
        print("Step 7: Running eval...")
        from tests.e2e_scripts._lifecycle import run_eval_internal  # noqa: E402
        run_eval_internal(workspace, "local-file-hasher")

        # 6) package - use internal helper
        print("Step 8: Packaging...")
        package_path = package_tool(workspace, "local-file-hasher")
        assert_file_exists(package_path)

        assert_zip_contains(
            package_path, ["toolforge.yaml", "tool.py", "skill/SKILL.md"]
        )
        assert_zip_contains(package_path, ["evals/task_config.json"])
        assert_zip_contains(package_path, ["SECURITY.md"])
        assert_zip_excludes(package_path, ["outputs/"])

        # 9) registry check - use internal helper
        print("Step 11: Checking registry...")
        assert_registry_packaged(workspace, "local-file-hasher")

        print("\n✓ All E2E steps passed.")

        # Check for leaked processes
        assert_no_leaked_processes()

    print("Local file hasher e2e lifecycle completed successfully!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
