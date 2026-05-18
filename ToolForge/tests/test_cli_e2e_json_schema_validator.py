"""CLI end-to-end smoke for json-schema-validator proof path."""
from __future__ import annotations

import json
import zipfile
from pathlib import Path

import pytest

from apps.cli.toolforge_cli.test_helpers import combined_output, run_toolforge, strip_ansi


@pytest.mark.e2e_isolated
def test_cli_e2e_json_schema_validator(tmp_path: Path) -> None:
    def invoke(args: list[str]):
        return run_toolforge(args, cwd=tmp_path)

    result = invoke(["init", str(tmp_path)])
    assert result.returncode == 0, combined_output(result)

    result = invoke(
        [
            "new",
            "tool",
            "--from-prompt",
            "Create a tool that validates JSON files against a schema",
        ]
    )
    assert result.returncode == 0, combined_output(result)

    tool_dir = tmp_path / "tools" / "generated" / "json-schema-validator"
    assert (tool_dir / "toolforge.yaml").exists()
    assert (tool_dir / "examples" / "schema.json").exists()
    assert (tool_dir / "examples" / "data_valid.json").exists()

    result = invoke(["generate", "mcp", "json-schema-validator"])
    assert result.returncode == 0, combined_output(result)
    result = invoke(["generate", "skill", "json-schema-validator"])
    assert result.returncode == 0, combined_output(result)
    result = invoke(["generate", "eval", "json-schema-validator"])
    assert result.returncode == 0, combined_output(result)

    result = invoke(["validate", "json-schema-validator"])
    assert result.returncode == 0, combined_output(result)

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
    assert result.returncode == 0, combined_output(result)
    clean = strip_ansi(result.stdout)
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
    assert result.returncode != 0
    assert "Path validation failed" in combined_output(result)

    result = invoke(["eval", "json-schema-validator"])
    assert result.returncode == 0, combined_output(result)

    result = invoke(["package", "json-schema-validator"])
    assert result.returncode == 0, combined_output(result)

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

    registry_path = tmp_path / "toolforge_registry.json"
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    metadata = registry["json-schema-validator"]["metadata"]
    assert metadata["status"] == "packaged"
    assert metadata["last_run_type"] == "safety_test"
    assert metadata["operational_last_run_success"] is True
    assert metadata["eval_score"] is not None
