"""CLI end-to-end smoke for json-schema-validator proof path."""
from __future__ import annotations

import json
import re
import zipfile
from pathlib import Path

from click.testing import CliRunner

from apps.cli.toolforge_cli.main import cli


_ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")


def _strip_ansi(text: str) -> str:
    return _ANSI_RE.sub("", text)


def test_cli_e2e_json_schema_validator(tmp_path: Path) -> None:
    runner = CliRunner()

    def invoke(args: list[str]):
        return runner.invoke(cli, args, catch_exceptions=False)

    result = invoke(["init", str(tmp_path)])
    assert result.exit_code == 0, result.output

    old_cwd = Path.cwd()
    try:
        import os

        os.chdir(tmp_path)

        result = invoke(
            [
                "new",
                "tool",
                "--from-prompt",
                "Create a tool that validates JSON files against a schema",
            ]
        )
        assert result.exit_code == 0, result.output

        tool_dir = tmp_path / "tools" / "generated" / "json-schema-validator"
        assert (tool_dir / "toolforge.yaml").exists()
        assert (tool_dir / "examples" / "schema.json").exists()
        assert (tool_dir / "examples" / "data_valid.json").exists()

        result = invoke(["generate", "mcp", "json-schema-validator"])
        assert result.exit_code == 0, result.output
        result = invoke(["generate", "skill", "json-schema-validator"])
        assert result.exit_code == 0, result.output
        result = invoke(["generate", "eval", "json-schema-validator"])
        assert result.exit_code == 0, result.output

        result = invoke(["validate", "json-schema-validator"])
        assert result.exit_code == 0, result.output

        result = invoke(
            [
                "run",
                "json-schema-validator",
                "--input",
                "data_path=examples/data_valid.json",
                "--input",
                "schema_path=examples/schema.json",
            ]
        )
        assert result.exit_code == 0, result.output
        clean = _strip_ansi(result.output)
        assert '"valid": true' in clean

        result = invoke(
            [
                "run",
                "json-schema-validator",
                "--input",
                "data_path=../../../etc/passwd",
                "--input",
                "schema_path=examples/schema.json",
            ]
        )
        assert result.exit_code != 0
        assert "Path validation failed" in result.output

        result = invoke(["eval", "json-schema-validator"])
        assert result.exit_code == 0, result.output

        result = invoke(["package", "json-schema-validator"])
        assert result.exit_code == 0, result.output

        dist_zip = tmp_path / "dist" / "json-schema-validator-0.1.0.zip"
        assert dist_zip.exists()
        with zipfile.ZipFile(dist_zip) as zf:
            names = set(zf.namelist())
            assert "toolforge.yaml" in names
            assert "tool.py" in names
            assert "skill/SKILL.md" in names
            assert "evals/cases/case-01-valid.json" in names
            assert "SECURITY.md" in names
            assert all(not name.startswith("outputs/") for name in names)

        registry = json.loads((tmp_path / "toolforge_registry.json").read_text(encoding="utf-8"))
        metadata = registry["json-schema-validator"]["metadata"]
        assert metadata["status"] == "packaged"
        assert metadata["last_run_type"] == "safety_test"
        assert metadata["operational_last_run_success"] is True
        assert metadata["eval_score"] is not None
    finally:
        import os

        os.chdir(old_cwd)
