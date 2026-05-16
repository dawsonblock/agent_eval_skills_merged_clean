"""CLI regression tests for validation and new-tool UX behavior."""
from __future__ import annotations

from pathlib import Path

from click.testing import CliRunner

from apps.cli.toolforge_cli.main import cli


def test_new_tool_duplicate_slug_fails_gracefully(tmp_path: Path) -> None:
    runner = CliRunner()

    result = runner.invoke(cli, ["init", str(tmp_path)], catch_exceptions=False)
    assert result.exit_code == 0, result.output

    old_cwd = Path.cwd()
    try:
        import os

        os.chdir(tmp_path)
        first = runner.invoke(
            cli,
            [
                "new",
                "tool",
                "--from-prompt",
                "Create a tool that cleans CSV files",
            ],
            catch_exceptions=False,
        )
        assert first.exit_code == 0, first.output

        second = runner.invoke(
            cli,
            [
                "new",
                "tool",
                "--from-prompt",
                "Create a tool that cleans CSV files",
            ],
            catch_exceptions=False,
        )
        assert second.exit_code == 1
        assert "Tool scaffold already exists" in second.output
        assert "--overwrite" in second.output
    finally:
        import os

        os.chdir(old_cwd)


def test_validate_fails_when_tests_directory_missing(tmp_path: Path) -> None:
    runner = CliRunner()

    result = runner.invoke(cli, ["init", str(tmp_path)], catch_exceptions=False)
    assert result.exit_code == 0, result.output

    old_cwd = Path.cwd()
    try:
        import os

        os.chdir(tmp_path)
        result = runner.invoke(
            cli,
            [
                "new",
                "tool",
                "--from-prompt",
                "Create a tool that cleans CSV files",
            ],
            catch_exceptions=False,
        )
        assert result.exit_code == 0, result.output

        tool_dir = tmp_path / "tools" / "generated" / "csv-cleaner"
        (tool_dir / "tests").rename(tool_dir / "tests_backup")

        runner.invoke(cli, ["generate", "mcp", "csv-cleaner"], catch_exceptions=False)
        runner.invoke(cli, ["generate", "skill", "csv-cleaner"], catch_exceptions=False)
        runner.invoke(cli, ["generate", "eval", "csv-cleaner"], catch_exceptions=False)

        validate = runner.invoke(
            cli,
            ["validate", "csv-cleaner"],
            catch_exceptions=False,
        )
        assert validate.exit_code == 1
        assert "Missing tests/ directory" in validate.output
    finally:
        import os

        os.chdir(old_cwd)