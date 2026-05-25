from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

from skillforge_ai.chat_runtime import ChatRuntime
from skillforge_ai.planner import PlannerResult


def _plan(mode: str, skill_name: str = "generated-skill") -> PlannerResult:
    return PlannerResult(
        intent=mode,
        skill_name=skill_name,
        category="custom",
        requires_tool_code=False,
        requires_mcp=False,
        permissions=["read_files"],
        risk_level="low",
        files_to_create=[],
        validation_plan=[],
        mode=mode,
    )


def test_handle_message_routes_list_mode(tmp_path: Path):
    runtime = ChatRuntime(workspace_root=tmp_path)
    runtime._planner = MagicMock()
    runtime._orchestrator = MagicMock()

    runtime._planner.build_plan.return_value = _plan("list_skills")
    runtime._orchestrator.chat.return_value = "skills listed"

    result = runtime.handle_message("list")

    runtime._orchestrator.chat.assert_called_once_with("list all skills")
    assert result["mode"] == "list_skills"
    assert result["response"] == "skills listed"


def test_handle_message_routes_validate_workspace(tmp_path: Path):
    runtime = ChatRuntime(workspace_root=tmp_path)
    runtime._planner = MagicMock()
    runtime._orchestrator = MagicMock()

    runtime._planner.build_plan.return_value = _plan("validate_workspace")
    runtime._orchestrator.chat.return_value = "Workspace health report"

    result = runtime.handle_message("validate workspace")

    runtime._orchestrator.chat.assert_called_once_with("doctor workspace")
    assert result["mode"] == "validate_workspace"
    assert "health" in result["response"].lower()


def test_handle_message_routes_call_tool_to_run(tmp_path: Path):
    runtime = ChatRuntime(workspace_root=tmp_path)
    runtime._planner = MagicMock()
    runtime._orchestrator = MagicMock()

    runtime._planner.build_plan.return_value = _plan(
        "call_tool",
        skill_name="csv-cleaner",
    )
    runtime._orchestrator.chat.return_value = "Tool executed"

    result = runtime.handle_message("call tool csv-cleaner")

    runtime._orchestrator.chat.assert_called_once_with("run csv-cleaner")
    assert result["mode"] == "call_tool"
    assert result["response"] == "Tool executed"


def test_extract_skill_slug_uses_fallback_if_needed(tmp_path: Path):
    runtime = ChatRuntime(workspace_root=tmp_path)
    slug = runtime._extract_skill_slug("call tool", fallback="report-builder")
    assert slug == "report-builder"
