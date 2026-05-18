"""CLI end-to-end smoke for local-file-hasher proof path."""
from __future__ import annotations

import json
import zipfile
from pathlib import Path

import pytest

from apps.cli.toolforge_cli.test_helpers import combined_output, run_toolforge, strip_ansi


@pytest.mark.e2e_isolated
def test_cli_e2e_local_file_hasher(tmp_path: Path) -> None:
    def invoke(args: list[str]):
        return run_toolforge(args, cwd=tmp_path)

    result = invoke(["init", str(tmp_path)])
    assert result.returncode == 0, combined_output(result)

    result = invoke(
        [
            "new",
            "tool",
            "--from-prompt",
            "Create a tool that computes SHA256 checksums of local files",
        ]
    )
    assert result.returncode == 0, combined_output(result)

    tool_dir = tmp_path / "tools" / "generated" / "local-file-hasher"
    assert (tool_dir / "toolforge.yaml").exists()
    assert (tool_dir / "examples" / "sample.txt").exists()

    result = invoke(["generate", "mcp", "local-file-hasher"])
    assert result.returncode == 0, combined_output(result)
    result = invoke(["generate", "skill", "local-file-hasher"])
    assert result.returncode == 0, combined_output(result)
    result = invoke(["generate", "eval", "local-file-hasher"])
    assert result.returncode == 0, combined_output(result)

    result = invoke(["validate", "local-file-hasher"])
    assert result.returncode == 0, combined_output(result)

    result = invoke(
        [
            "run",
            "local-file-hasher",
            "--input",
            "file_path=examples/sample.txt",
        ]
    )
    assert result.returncode == 0, combined_output(result)
    clean = strip_ansi(result.stdout)
    assert '"algorithm": "sha256"' in clean

    result = invoke(
        [
            "run",
            "local-file-hasher",
            "--input",
            "file_path=../../../etc/passwd",
        ]
    )
    assert result.returncode != 0
    assert "Path validation failed" in combined_output(result)

    result = invoke(["eval", "local-file-hasher"])
    assert result.returncode == 0, combined_output(result)

    result = invoke(["package", "local-file-hasher"])
    assert result.returncode == 0, combined_output(result)

    dist_zip = tmp_path / "dist" / "local-file-hasher-0.1.0.zip"
    assert dist_zip.exists()
    with zipfile.ZipFile(dist_zip) as zf:
        names = set(zf.namelist())
        assert "toolforge.yaml" in names
        assert "tool.py" in names
        assert "skill/SKILL.md" in names
        assert "evals/cases/case-01-success.json" in names
        assert "SECURITY.md" in names
        assert all(not name.startswith("outputs/") for name in names)

    registry_path = tmp_path / "toolforge_registry.json"
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    metadata = registry["local-file-hasher"]["metadata"]
    assert metadata["status"] == "packaged"
    assert metadata["last_run_type"] == "safety_test"
    assert metadata["operational_last_run_success"] is True
    assert metadata["eval_score"] is not None
