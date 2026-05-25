from __future__ import annotations
# mypy: disable-error-code=import-untyped

import zipfile
from pathlib import Path
from unittest.mock import MagicMock
import json
from types import SimpleNamespace

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


def test_handle_message_install_skill_success(tmp_path: Path):
    runtime = ChatRuntime(workspace_root=tmp_path)
    runtime._planner = MagicMock()

    archive = tmp_path / "csv-cleaner-0.1.0.zip"
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("tool.py", "print('ok')\n")

    runtime._planner.build_plan.return_value = _plan("install_skill")
    result = runtime.handle_message(f"install {archive}")

    assert result["mode"] == "install_skill"
    assert "Installed 'csv-cleaner'" in result["response"]


def test_handle_message_install_skill_missing_archive(tmp_path: Path):
    runtime = ChatRuntime(workspace_root=tmp_path)
    runtime._planner = MagicMock()

    runtime._planner.build_plan.return_value = _plan("install_skill")
    result = runtime.handle_message("install missing.zip")

    assert result["mode"] == "install_skill"
    assert "file not found" in result["response"]


def test_extract_zip_path_from_quoted_message(tmp_path: Path):
    runtime = ChatRuntime(workspace_root=tmp_path)
    path = runtime._extract_zip_path("install \"/tmp/my skill.zip\"")
    assert path is not None
    assert path.as_posix().endswith("/tmp/my skill.zip")


def test_phase12_mvp_chat_flow_with_pronouns(tmp_path: Path, monkeypatch):
    runtime = ChatRuntime(workspace_root=tmp_path)

    plans = [
        _plan("build_skill", skill_name="csv-cleaner"),
        _plan("validate_skill", skill_name="generated-skill"),
        _plan("run_skill", skill_name="generated-skill"),
        _plan("package_skill", skill_name="generated-skill"),
        _plan("inspect_skill", skill_name="generated-skill"),
    ]
    runtime._planner = MagicMock()
    runtime._planner.build_plan.side_effect = plans

    monkeypatch.setattr(
        "skillforge_ai.commands.create.run_create",
        lambda workspace_root, prompt, provider, name=None: (
            tmp_path / "tools" / "generated" / "csv-cleaner",
            SimpleNamespace(name="csv-cleaner"),
        ),
    )
    monkeypatch.setattr(
        "skillforge_ai.commands.validate.run_validate",
        lambda workspace_root, slug, repair, provider: SimpleNamespace(passed=True),
    )
    monkeypatch.setattr(
        "skillforge_ai.commands.run.run_skill",
        lambda workspace_root, slug, inputs: SimpleNamespace(
            exit_code=0,
            output=json.dumps({"status": "passed", "skill": slug}),
            error="",
        ),
    )
    monkeypatch.setattr(
        "skillforge_ai.commands.package.run_package",
        lambda workspace_root, slug, output=None: (
            tmp_path / ".skillforge" / "packages" / f"{slug}-0.1.0.zip",
            "abc123",
        ),
    )

    class _SkillReg:
        def __init__(self, _root: Path):
            pass

        def get(self, slug: str):
            return {"name": slug, "tool_refs": ["csv_cleaner_tool"]}

    class _ToolReg:
        def __init__(self, _root: Path):
            pass

        def list_registered_tools(self):
            return [{"name": "csv_cleaner_tool", "entrypoint": "skills/csv-cleaner/tool/main.py"}]

    monkeypatch.setattr("skillforge_ai.chat_runtime.SkillRegistry", _SkillReg)
    monkeypatch.setattr("skillforge_ai.chat_runtime.SkillForgeRegistry", _ToolReg)

    build = runtime.handle_message("Build me a skill that cleans CSV files.")
    validate = runtime.handle_message("Validate that skill.")
    run = runtime.handle_message("Run it on this file sample.csv")
    package = runtime.handle_message("Package it.")
    inspect = runtime.handle_message("Show me what tools it controls.")

    assert build["response"] == "Built skill 'csv-cleaner'."
    assert "Validation passed" in validate["response"]
    assert "Run passed for 'csv-cleaner'" in run["response"]
    assert "Packaged 'csv-cleaner'" in package["response"]
    assert "csv_cleaner_tool" in inspect["response"]
