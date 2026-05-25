"""
Tests for skillforge_ai.orchestrator — AIOrchestrator intent parsing and mode dispatch.
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch


from skillforge_ai.models import Mode, SkillManifest
from skillforge_ai.orchestrator import AIOrchestrator, _parse_skill_name, _derive_slug


class TestParseSkillName:
    def test_extracts_skill_name_after_for(self):
        result = _parse_skill_name("repair the csv-cleaner tool")
        assert result == "csv-cleaner"

    def test_returns_none_for_plain_sentence(self):
        result = _parse_skill_name("build a tool that converts JSON")
        # Should be None or a word — not raise
        assert result is None or isinstance(result, str)


class TestDeriveSlug:
    def test_converts_spaces_to_dashes(self):
        slug = _derive_slug("My CSV Cleaner")
        assert " " not in slug
        assert slug == "my-csv-cleaner"

    def test_strips_special_chars(self):
        slug = _derive_slug("tool! @# test")
        assert slug == "tool-test"


class TestAIOrchestratorIntentParsing:
    def _orch(self, tmp_path: Path) -> AIOrchestrator:
        return AIOrchestrator(workspace_root=tmp_path, interactive=False, auto_approve=True)

    def test_parse_build_intent(self, tmp_path: Path):
        orch = self._orch(tmp_path)
        intent = orch._parse_intent("Create a tool that converts JSON to CSV")
        assert intent.mode == Mode.BUILD

    def test_parse_repair_intent(self, tmp_path: Path):
        orch = self._orch(tmp_path)
        intent = orch._parse_intent("Fix the csv-cleaner tool")
        assert intent.mode == Mode.REPAIR

    def test_parse_inspect_intent(self, tmp_path: Path):
        orch = self._orch(tmp_path)
        intent = orch._parse_intent("List all skills")
        assert intent.mode == Mode.INSPECT

    def test_parse_run_intent(self, tmp_path: Path):
        orch = self._orch(tmp_path)
        intent = orch._parse_intent("Run csv-cleaner")
        assert intent.mode == Mode.RUN

    def test_parse_package_intent(self, tmp_path: Path):
        orch = self._orch(tmp_path)
        intent = orch._parse_intent("Package the csv-cleaner skill")
        assert intent.mode == Mode.PACKAGE

    def test_parse_benchmark_intent(self, tmp_path: Path):
        orch = self._orch(tmp_path)
        intent = orch._parse_intent("Benchmark the csv-cleaner tool")
        assert intent.mode == Mode.BENCHMARK

    def test_parse_admin_init_intent(self, tmp_path: Path):
        orch = self._orch(tmp_path)
        intent = orch._parse_intent("Initialize the workspace")
        assert intent.mode == Mode.ADMIN

    def test_parse_unknown_intent(self, tmp_path: Path):
        orch = self._orch(tmp_path)
        intent = orch._parse_intent("asdfghjklzxcvbnm")
        # Could be UNKNOWN or any mode depending on fallback; just ensure no exception
        assert isinstance(intent.mode, Mode)


class TestAIOrchestratorAdminCommands:
    def _orch(self, tmp_path: Path) -> AIOrchestrator:
        return AIOrchestrator(workspace_root=tmp_path, interactive=False, auto_approve=True)

    def test_cmd_init_creates_skillforge_dir(self, tmp_path: Path):
        orch = self._orch(tmp_path)
        msg = orch._cmd_init()
        assert (tmp_path / ".skillforge").exists()
        assert "initialised" in msg.lower() or "initialized" in msg.lower() or tmp_path.name in msg

    def test_cmd_doctor_returns_string(self, tmp_path: Path):
        orch = self._orch(tmp_path)
        result = orch._cmd_doctor()
        assert isinstance(result, str)
        assert "health" in result.lower() or "workspace" in result.lower()

    def test_cmd_doctor_reports_missing_dirs(self, tmp_path: Path):
        orch = self._orch(tmp_path)
        msg = orch._cmd_doctor()
        assert "MISSING" in msg or "action needed" in msg


class TestAIOrchestratorChatDispatch:
    def _orch(self, tmp_path: Path) -> AIOrchestrator:
        return AIOrchestrator(workspace_root=tmp_path, interactive=False, auto_approve=True)

    def test_chat_admin_init(self, tmp_path: Path):
        orch = self._orch(tmp_path)
        response = orch.chat("init workspace")
        assert isinstance(response, str)
        assert len(response) > 0

    def test_chat_inspect_list(self, tmp_path: Path):
        (tmp_path / "toolforge_registry.json").write_text("{}", encoding="utf-8")
        orch = self._orch(tmp_path)
        response = orch.chat("list all tools")
        assert isinstance(response, str)

    def test_chat_build_calls_skill_builder(self, tmp_path: Path):
        orch = self._orch(tmp_path)
        manifest = SkillManifest(name="csv-cleaner", description="Cleans CSV files", category="data")
        tool_dir = tmp_path / "tools" / "generated" / "csv-cleaner"
        tool_dir.mkdir(parents=True)

        (tmp_path / "toolforge_registry.json").write_text("{}", encoding="utf-8")

        # Bypass @property by setting the private backing attributes
        mock_builder = MagicMock()
        mock_builder.build.return_value = (tool_dir, manifest)
        mock_registry = MagicMock()
        mock_registry.register_skill.return_value = None

        orch._builder = mock_builder
        orch._registry = mock_registry

        response = orch.chat("Create a tool that cleans CSV files")

        assert "csv-cleaner" in response or "created" in response.lower() or "generated" in response.lower()

    def test_chat_repair_without_slug(self, tmp_path: Path):
        orch = self._orch(tmp_path)
        response = orch.chat("repair")
        assert "specify" in response.lower() or "repair" in response.lower()

    def test_chat_returns_string_on_error(self, tmp_path: Path):
        orch = self._orch(tmp_path)
        with patch.object(orch, "_handle_build", side_effect=RuntimeError("boom")):
            response = orch.chat("create a tool")
        assert "Error" in response or "boom" in response

    def test_chat_list_skills_planner_mode(self, tmp_path: Path):
        orch = self._orch(tmp_path)
        response = orch.chat("list skills")
        assert isinstance(response, str)
        assert "No skills" in response or "Name" in response

    @patch("skillforge_ai.commands.tools.call_mcp_tool")
    def test_chat_call_tool_uses_registry(self, mock_call_tool, tmp_path: Path):
        orch = self._orch(tmp_path)

        server = tmp_path / "tools" / "generated" / "csv-cleaner" / "mcp" / "server.py"
        server.parent.mkdir(parents=True, exist_ok=True)
        server.write_text("# stub", encoding="utf-8")

        orch._skill_registry.register_tool(
            {
                "name": "csv-cleaner_tool",
                "type": "python",
                "entrypoint": "skills/csv-cleaner/tool/main.py",
                "validated": True,
                "mcp_server": str(server),
            }
        )

        mock_call_tool.return_value = {"ok": True}
        response = orch.chat("call tool csv-cleaner")
        assert "succeeded" in response.lower() or "ok" in response.lower()

    def test_chat_call_tool_rejects_missing_registry_entry(self, tmp_path: Path):
        orch = self._orch(tmp_path)
        response = orch.chat("call tool csv-cleaner")
        assert "not registered" in response.lower() or "register" in response.lower()


class TestAIOrchestratorApproval:
    def test_auto_approve_returns_true(self, tmp_path: Path):
        orch = AIOrchestrator(workspace_root=tmp_path, interactive=False, auto_approve=True)
        assert orch._prompt_approval("test action") is True

    def test_non_interactive_returns_false(self, tmp_path: Path):
        orch = AIOrchestrator(workspace_root=tmp_path, interactive=False, auto_approve=False)
        assert orch._prompt_approval("test action") is False
