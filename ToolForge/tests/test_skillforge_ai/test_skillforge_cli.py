"""
Tests for skillforge_cli.main — Click CLI with CliRunner.
"""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from apps.cli.skillforge_cli.main import main


def _make_workspace(tmp_path: Path) -> Path:
    """Create a minimal workspace for CLI tests."""
    (tmp_path / ".skillforge").mkdir()
    (tmp_path / ".toolforge").mkdir()
    (tmp_path / "toolforge_registry.json").write_text("{}", encoding="utf-8")
    for d in ("tools/generated", "skills/generated", "evals/generated", "dist"):
        (tmp_path / d).mkdir(parents=True, exist_ok=True)
    return tmp_path


@pytest.fixture()
def runner() -> CliRunner:
    return CliRunner(mix_stderr=False)


@pytest.fixture()
def ws(tmp_path: Path) -> Path:
    return _make_workspace(tmp_path)


class TestInitCommand:
    def test_init_creates_skillforge_dir(self, runner: CliRunner, tmp_path: Path):
        result = runner.invoke(
            main,
            ["--workspace", str(tmp_path), "init", str(tmp_path)],
        )
        assert result.exit_code == 0 or (tmp_path / ".skillforge").exists()

    def test_init_already_exists(self, runner: CliRunner, ws: Path):
        result = runner.invoke(
            main,
            ["--workspace", str(ws), "init", str(ws)],
        )
        assert result.exit_code == 0
        assert "already" in result.output.lower() or "workspace" in result.output.lower()

    def test_init_uses_workspace_when_directory_omitted(self, runner: CliRunner, tmp_path: Path):
        ws = tmp_path / "custom-ws"
        ws.mkdir(parents=True)

        result = runner.invoke(
            main,
            ["--workspace", str(ws), "init"],
        )

        assert result.exit_code == 0
        assert (ws / ".skillforge").exists()


class TestDoctorCommand:
    def test_doctor_runs(self, runner: CliRunner, ws: Path):
        result = runner.invoke(
            main,
            ["--workspace", str(ws), "doctor"],
        )
        assert result.exit_code == 0
        assert "health" in result.output.lower() or "workspace" in result.output.lower()


class TestListCommand:
    def test_list_empty(self, runner: CliRunner, ws: Path):
        result = runner.invoke(
            main,
            ["--workspace", str(ws), "list"],
        )
        assert result.exit_code == 0

    def test_list_json_output(self, runner: CliRunner, ws: Path):
        result = runner.invoke(
            main,
            ["--workspace", str(ws), "list", "--json"],
        )
        assert result.exit_code == 0
        # Output should be valid JSON
        data = json.loads(result.output)
        assert isinstance(data, list)


class TestInspectCommand:
    def test_inspect_missing_slug_exits_with_error(self, runner: CliRunner, ws: Path):
        result = runner.invoke(
            main,
            ["--workspace", str(ws), "inspect", "nonexistent"],
        )
        assert result.exit_code != 0

    def test_inspect_existing_skill(self, runner: CliRunner, ws: Path):
        from skillforge_ai.tool_registry import SkillForgeRegistry
        from skillforge_ai.models import SkillManifest

        tool_dir = ws / "tools" / "generated" / "csv-cleaner"
        tool_dir.mkdir(parents=True, exist_ok=True)

        reg = SkillForgeRegistry(ws)
        reg.register_skill(SkillManifest(name="csv-cleaner", description="Cleans CSV", category="data"), tool_dir)

        result = runner.invoke(
            main,
            ["--workspace", str(ws), "inspect", "csv-cleaner"],
        )
        assert result.exit_code == 0
        assert "csv-cleaner" in result.output


class TestCreateCommand:
    @patch("skillforge_ai.skill_builder.SkillBuilder.build")
    def test_create_invokes_builder(self, mock_build, runner: CliRunner, ws: Path):
        from skillforge_ai.models import SkillManifest

        manifest = SkillManifest(name="csv-cleaner", description="Cleans CSV", category="data")
        tool_dir = ws / "tools" / "generated" / "csv-cleaner"
        tool_dir.mkdir(parents=True, exist_ok=True)
        mock_build.return_value = (tool_dir, manifest)

        result = runner.invoke(
            main,
            ["--workspace", str(ws), "--yes", "create", "a CSV cleaning tool"],
        )
        assert result.exit_code == 0 or mock_build.called


class TestValidateCommand:
    @patch("skillforge_ai.validation_runner.ValidationRunner.validate")
    def test_validate_passed(self, mock_validate, runner: CliRunner, ws: Path):
        from skillforge_ai.models import ValidationReport

        mock_validate.return_value = ValidationReport(slug="csv-cleaner", passed=True)

        result = runner.invoke(
            main,
            ["--workspace", str(ws), "validate", "csv-cleaner"],
        )
        assert result.exit_code == 0
        assert "PASSED" in result.output

    @patch("skillforge_ai.validation_runner.ValidationRunner.validate")
    def test_validate_failed_exits_nonzero(self, mock_validate, runner: CliRunner, ws: Path):
        from skillforge_ai.models import ValidationReport

        mock_validate.return_value = ValidationReport(
            slug="csv-cleaner",
            passed=False,
            errors=["schema error"],
        )

        result = runner.invoke(
            main,
            ["--workspace", str(ws), "validate", "csv-cleaner"],
        )
        assert result.exit_code != 0
        assert "FAILED" in result.output


class TestPackageCommand:
    def test_package_missing_tool_exits_error(self, runner: CliRunner, ws: Path):
        result = runner.invoke(
            main,
            ["--workspace", str(ws), "package", "nonexistent"],
        )
        assert result.exit_code != 0

    def test_package_existing_tool_creates_zip(self, runner: CliRunner, ws: Path):
        tool_dir = ws / "tools" / "generated" / "csv-cleaner"
        tool_dir.mkdir(parents=True, exist_ok=True)
        (tool_dir / "main.py").write_text("# stub", encoding="utf-8")

        from skillforge_ai.tool_registry import SkillForgeRegistry
        from skillforge_ai.models import SkillManifest

        SkillForgeRegistry(ws).register_skill(
            SkillManifest(name="csv-cleaner", description="Cleans CSV", category="data"),
            tool_dir,
        )

        result = runner.invoke(
            main,
            ["--workspace", str(ws), "--yes", "package", "csv-cleaner"],
        )
        assert result.exit_code == 0
        zips = list((ws / "dist").glob("*.zip"))
        assert len(zips) == 1


class TestMCPSmokeCommand:
    @patch("skillforge_ai.mcp_controller.MCPController.smoke_test")
    def test_mcp_smoke_pass(self, mock_smoke, runner: CliRunner, ws: Path):
        mock_smoke.return_value = True

        server = ws / "tools" / "generated" / "csv-cleaner" / "mcp" / "server.py"
        server.parent.mkdir(parents=True, exist_ok=True)
        server.write_text("# stub", encoding="utf-8")

        result = runner.invoke(
            main,
            [
                "--workspace", str(ws),
                "mcp", "smoke", "csv-cleaner",
                "--server-path", str(server),
            ],
        )
        assert result.exit_code == 0
        assert "passed" in result.output.lower()


class TestRepairCommand:
    @patch("skillforge_ai.validation_runner.ValidationRunner.repair_loop")
    def test_repair_passed(self, mock_repair, runner: CliRunner, ws: Path):
        from skillforge_ai.models import ValidationReport

        mock_repair.return_value = ValidationReport(slug="csv-cleaner", passed=True)

        result = runner.invoke(
            main,
            ["--workspace", str(ws), "repair", "csv-cleaner"],
        )
        assert result.exit_code == 0
        assert "PASSED" in result.output


class TestChatCommand:
    @patch("skillforge_ai.chat_runtime.ChatRuntime.run_loop")
    def test_chat_invokes_repl(self, mock_repl, runner: CliRunner, ws: Path):
        result = runner.invoke(
            main,
            ["--workspace", str(ws), "chat"],
        )
        assert result.exit_code == 0
        mock_repl.assert_called_once()
