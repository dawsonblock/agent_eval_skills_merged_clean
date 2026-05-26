#!/usr/bin/env python3
"""E2E script for csv-cleaner proof path - runs in isolated process."""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from datetime import datetime, timezone
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
    """Run the full csv-cleaner e2e lifecycle."""
    parser = argparse.ArgumentParser(description="Run csv-cleaner e2e lifecycle.")
    parser.add_argument(
        "--json-output",
        dest="json_output",
        default=None,
        help="Optional path for writing a machine-readable summary JSON.",
    )
    args = parser.parse_args()

    step_results: list[dict[str, str]] = []

    def _mark_step(name: str) -> None:
        step_results.append({"name": name, "status": "passed"})

    print("Starting csv-cleaner e2e lifecycle...")

    # Create temporary workspace
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)

        # 1) init - use internal helper
        print("Step 1: Initializing workspace...")
        workspace = create_workspace(tmp_path)
        _mark_step("init")
        print(f"Workspace created at: {workspace}")

        # 2) new tool from prompt - use internal helper
        print("Step 2: Creating csv-cleaner tool...")
        spec = generate_tool_from_prompt(
            workspace, "Create a tool that cleans CSV files", slug="csv-cleaner"
        )
        _mark_step("create")
        print(f"Tool spec created: {spec.slug}")

        tool_dir = workspace / "tools" / "generated" / "csv-cleaner"
        assert_file_exists(tool_dir / "toolforge.yaml")
        assert_file_exists(tool_dir / "tool.py")
        assert_file_exists(tool_dir / "examples" / "input.csv")

        # 3) generate mcp/skill/eval - use internal helpers
        print("Step 3: Generating MCP...")
        generate_mcp(workspace, "csv-cleaner")
        _mark_step("generate_mcp")
        assert_file_exists(tool_dir / "mcp" / "server.py")

        print("Step 4: Generating skill...")
        generate_skill(workspace, "csv-cleaner")
        _mark_step("generate_skill")
        assert_file_exists(tool_dir / "skill" / "SKILL.md")

        print("Step 5: Generating eval...")
        generate_eval(workspace, "csv-cleaner")
        _mark_step("generate_eval")
        assert_file_exists(
            tool_dir / "evals" / "cases" / "case-01-success.json"
        )

        # 4) validate - use internal helper
        print("Step 6: Validating...")
        validate_tool(workspace, "csv-cleaner")
        _mark_step("validate")

        # 5) package - use internal helper (eval coverage moved to focused command-exit tests)
        print("Step 7: Packaging...")
        package_path = package_tool(workspace, "csv-cleaner")
        _mark_step("package")
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
        _mark_step("registry")

        print("\n✓ All E2E steps passed.")

        # Check for leaked processes
        assert_no_leaked_processes()
        _mark_step("process_hygiene")

        if args.json_output:
            output_path = Path(args.json_output)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            payload = {
                "summary_version": "2026-05-25",
                "component": "skillforge_ai",
                "artifact_type": "csv_cleaner_e2e_summary",
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "overall_status": "passed",
                "workspace_mode": "isolated_temp_workspace",
                "proof": {
                    "tool_slug": "csv-cleaner",
                    "tmp_workspace": str(workspace),
                    "package_path": str(package_path),
                    "steps": step_results,
                },
            }
            output_path.write_text(
                json.dumps(payload, indent=2, ensure_ascii=True) + "\n",
                encoding="utf-8",
            )
            print(f"Summary written: {output_path}")

    print("CSV cleaner e2e lifecycle completed successfully!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
