"""CLI end-to-end smoke for local-file-hasher proof path."""
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


def test_cli_e2e_local_file_hasher(tmp_path: Path) -> None:
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
                "Create a tool that computes SHA256 checksums of local files",
            ]
        )
        assert result.exit_code == 0, result.output

        tool_dir = tmp_path / "tools" / "generated" / "local-file-hasher"
        assert (tool_dir / "toolforge.yaml").exists()
        assert (tool_dir / "examples" / "sample.txt").exists()

        result = invoke(["generate", "mcp", "local-file-hasher"])
        assert result.exit_code == 0, result.output
        result = invoke(["generate", "skill", "local-file-hasher"])
        assert result.exit_code == 0, result.output
        result = invoke(["generate", "eval", "local-file-hasher"])
        assert result.exit_code == 0, result.output

        result = invoke(["validate", "local-file-hasher"])
        assert result.exit_code == 0, result.output

        result = invoke(
            [
                "run",
                "local-file-hasher",
                "--input",
                "file_path=examples/sample.txt",
            ]
        )
        assert result.exit_code == 0, result.output
        clean = _strip_ansi(result.output)
        assert '"algorithm": "sha256"' in clean

        result = invoke(
            [
                "run",
                "local-file-hasher",
                "--input",
                "file_path=../../../etc/passwd",
            ]
        )
        assert result.exit_code != 0
        assert "Path validation failed" in result.output

        result = invoke(["eval", "local-file-hasher"])
        assert result.exit_code == 0, result.output

        result = invoke(["package", "local-file-hasher"])
        assert result.exit_code == 0, result.output

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

        registry = json.loads((tmp_path / "toolforge_registry.json").read_text(encoding="utf-8"))
        metadata = registry["local-file-hasher"]["metadata"]
        assert metadata["status"] == "packaged"
        assert metadata["last_run_type"] == "safety_test"
        assert metadata["operational_last_run_success"] is True
        assert metadata["eval_score"] is not None
    finally:
        import os

        os.chdir(old_cwd)
