"""CLI end-to-end smoke for csv-cleaner proof path."""
from __future__ import annotations

import json
import zipfile
from pathlib import Path

from click.testing import CliRunner

from apps.cli.toolforge_cli.main import cli


def test_cli_e2e_csv_cleaner(tmp_path: Path) -> None:
    runner = CliRunner()

    def invoke(args: list[str]):
        return runner.invoke(cli, args, catch_exceptions=False)

    # 1) init
    result = invoke(["init", str(tmp_path)])
    assert result.exit_code == 0, result.output

    # Run all subsequent commands from workspace root.
    old_cwd = Path.cwd()
    try:
        import os

        os.chdir(tmp_path)

        # 2) new tool from prompt
        result = invoke(
            [
                "new",
                "tool",
                "--from-prompt",
                "Create a tool that cleans CSV files",
            ]
        )
        assert result.exit_code == 0, result.output

        tool_dir = tmp_path / "tools" / "generated" / "csv-cleaner"
        assert (tool_dir / "toolforge.yaml").exists()
        assert (tool_dir / "tool.py").exists()
        assert (tool_dir / "examples" / "input.csv").exists()

        # 3) generate mcp/skill/eval
        result = invoke(["generate", "mcp", "csv-cleaner"])
        assert result.exit_code == 0, result.output
        assert (tool_dir / "mcp" / "server.py").exists()

        result = invoke(["generate", "skill", "csv-cleaner"])
        assert result.exit_code == 0, result.output
        assert (tool_dir / "skill" / "SKILL.md").exists()

        result = invoke(["generate", "eval", "csv-cleaner"])
        assert result.exit_code == 0, result.output
        assert (tool_dir / "evals" / "cases" / "case-01-success.json").exists()

        # 4) validate
        result = invoke(["validate", "csv-cleaner"])
        assert result.exit_code == 0, result.output

        # 5) run success
        result = invoke(
            [
                "run",
                "csv-cleaner",
                "--input",
                "input_path=examples/input.csv",
            ]
        )
        assert result.exit_code == 0, result.output
        assert "cleaned_path" in result.output
        assert (tool_dir / "outputs" / "cleaned.csv").exists()

        # 6) run safety boundary
        result = invoke(
            [
                "run",
                "csv-cleaner",
                "--input",
                "input_path=../../../etc/passwd",
            ]
        )
        assert result.exit_code != 0
        assert "Path validation failed" in result.output

        # 7) eval
        result = invoke(["eval", "csv-cleaner"])
        assert result.exit_code == 0, result.output

        # 8) package
        result = invoke(["package", "csv-cleaner"])
        assert result.exit_code == 0, result.output

        dist_zip = tmp_path / "dist" / "csv-cleaner-0.1.0.zip"
        assert dist_zip.exists()
        with zipfile.ZipFile(dist_zip) as zf:
            names = set(zf.namelist())
            assert "toolforge.yaml" in names
            assert "tool.py" in names
            assert "mcp/server.py" in names
            assert "skill/SKILL.md" in names
            assert any(name.startswith("evals/") for name in names)
            assert "SECURITY.md" in names
            assert all("__pycache__" not in name for name in names)
            assert all(not name.endswith(".pyc") for name in names)
            assert all(".coverage" not in name for name in names)

        # 9) registry values advanced
        registry = json.loads((tmp_path / "toolforge_registry.json").read_text(encoding="utf-8"))
        metadata = registry["csv-cleaner"]["metadata"]
        assert metadata["mcp_path"]
        assert metadata["skill_path"]
        assert metadata["eval_path"]
        assert metadata["last_validation"]
        assert metadata["last_run"]
        assert metadata["last_run_success"] is False
        assert metadata["last_run_type"] == "safety_test"
        assert metadata["operational_last_run_success"] is True
        assert metadata["last_successful_run"]
        assert metadata["last_failed_run"]
        assert metadata["eval_score"] is not None
        assert metadata["package_path"]
    finally:
        import os

        os.chdir(old_cwd)
