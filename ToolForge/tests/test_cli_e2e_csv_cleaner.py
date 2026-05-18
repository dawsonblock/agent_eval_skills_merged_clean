"""CLI end-to-end smoke for csv-cleaner proof path."""
from __future__ import annotations

import json
import zipfile
from pathlib import Path

import pytest

from apps.cli.toolforge_cli.test_helpers import combined_output, run_toolforge


@pytest.mark.e2e_isolated
def test_cli_e2e_csv_cleaner(tmp_path: Path) -> None:
    def invoke(args: list[str]):
        return run_toolforge(args, cwd=tmp_path)

    # 1) init
    result = invoke(["init", str(tmp_path)])
    assert result.returncode == 0, combined_output(result)

    # 2) new tool from prompt
    result = invoke(
        [
            "new",
            "tool",
            "--from-prompt",
            "Create a tool that cleans CSV files",
        ]
    )
    assert result.returncode == 0, combined_output(result)

    tool_dir = tmp_path / "tools" / "generated" / "csv-cleaner"
    assert (tool_dir / "toolforge.yaml").exists()
    assert (tool_dir / "tool.py").exists()
    assert (tool_dir / "examples" / "input.csv").exists()

    # 3) generate mcp/skill/eval
    result = invoke(["generate", "mcp", "csv-cleaner"])
    assert result.returncode == 0, combined_output(result)
    assert (tool_dir / "mcp" / "server.py").exists()

    result = invoke(["generate", "skill", "csv-cleaner"])
    assert result.returncode == 0, combined_output(result)
    assert (tool_dir / "skill" / "SKILL.md").exists()

    result = invoke(["generate", "eval", "csv-cleaner"])
    assert result.returncode == 0, combined_output(result)
    assert (tool_dir / "evals" / "cases" / "case-01-success.json").exists()

    # 4) validate
    result = invoke(["validate", "csv-cleaner"])
    assert result.returncode == 0, combined_output(result)

    # 5) run success
    result = invoke(
        [
            "run",
            "csv-cleaner",
            "--input",
            "input_path=examples/input.csv",
        ]
    )
    assert result.returncode == 0, combined_output(result)
    assert "cleaned_path" in result.stdout
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
    assert result.returncode != 0
    assert "Path validation failed" in combined_output(result)

    # 7) eval
    result = invoke(["eval", "csv-cleaner"])
    assert result.returncode == 0, combined_output(result)

    # 8) package
    result = invoke(["package", "csv-cleaner"])
    assert result.returncode == 0, combined_output(result)

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
    assert metadata["operational_last_run_success"] is True
    assert metadata["last_successful_run"]
    assert metadata["last_failed_run"]
    assert metadata["eval_score"] is not None
    assert metadata["package_path"]
