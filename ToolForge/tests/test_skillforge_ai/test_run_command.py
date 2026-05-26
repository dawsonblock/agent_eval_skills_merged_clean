from __future__ import annotations
# mypy: disable-error-code=import-untyped

from pathlib import Path

import pytest

from packages.runners.tool_runner import ToolRunResult
from skillforge_ai.commands import run as run_module
from skillforge_ai.skill_registry import SkillRegistry
from skillforge_ai.tool_registry import SkillForgeRegistry


class _DummySpec:
    entry_point = "tool.py"


@pytest.fixture()
def ws(tmp_path: Path) -> Path:
    root = tmp_path.resolve()
    SkillRegistry(root).upsert({"name": "csv-cleaner"})
    return root


def _write_generated_tool(root: Path, slug: str) -> Path:
    tool_dir = root / "tools" / "generated" / slug
    tool_dir.mkdir(parents=True, exist_ok=True)
    (tool_dir / "toolforge.yaml").write_text("name: csv-cleaner\n", encoding="utf-8")
    return tool_dir


def test_run_skill_uses_registry_entrypoint(monkeypatch, ws: Path):
    captured: dict[str, object] = {}
    tool_dir = ws / "custom" / "runner"
    tool_dir.mkdir(parents=True, exist_ok=True)
    (tool_dir / "toolforge.yaml").write_text("name: csv-cleaner\n", encoding="utf-8")

    SkillForgeRegistry(ws).register_tool(
        {
            "name": "csv-cleaner_tool",
            "type": "python",
            "entrypoint": str(tool_dir / "tool.py"),
            "working_dir": str(tool_dir),
            "validated": True,
        }
    )

    def fake_validate_yaml_file(path: Path):
        captured["yaml_path"] = path
        return _DummySpec()

    def fake_run_tool(spec, resolved_tool_dir: Path, inputs: dict[str, str]):
        captured["tool_dir"] = resolved_tool_dir
        captured["inputs"] = inputs
        return ToolRunResult(output="ok", error="", elapsed_ms=1.0, exit_code=0)

    monkeypatch.setattr(run_module, "validate_yaml_file", fake_validate_yaml_file)
    monkeypatch.setattr(run_module, "run_tool", fake_run_tool)

    result = run_module.run_skill(ws, "csv-cleaner", {"input_path": "examples/input.csv"})

    assert result.exit_code == 0
    assert captured["tool_dir"] == tool_dir
    assert captured["yaml_path"] == tool_dir / "toolforge.yaml"


def test_run_skill_uses_skill_local_tool_dir(monkeypatch, ws: Path):
    captured: dict[str, object] = {}
    skill_tool_dir = ws / "skills" / "csv-cleaner" / "tool"
    skill_tool_dir.mkdir(parents=True, exist_ok=True)
    (skill_tool_dir / "main.py").write_text("print('ok')\n", encoding="utf-8")

    def fake_run_python_entrypoint(
        resolved_tool_dir: Path,
        entrypoint: Path | None,
        inputs: dict[str, str],
    ) -> ToolRunResult:
        captured["tool_dir"] = resolved_tool_dir
        captured["entrypoint"] = entrypoint
        captured["inputs"] = inputs
        return ToolRunResult(output="ok", error="", elapsed_ms=1.0, exit_code=0)

    monkeypatch.setattr(run_module, "_run_python_entrypoint", fake_run_python_entrypoint)

    result = run_module.run_skill(ws, "csv-cleaner", {"input_path": "examples/input.csv"})

    assert result.exit_code == 0
    assert captured["tool_dir"] == skill_tool_dir


def test_run_skill_falls_back_to_tools_generated(monkeypatch, ws: Path):
    captured: dict[str, object] = {}
    tool_dir = _write_generated_tool(ws, "csv-cleaner")

    def fake_validate_yaml_file(path: Path):
        captured["yaml_path"] = path
        return _DummySpec()

    def fake_run_tool(spec, resolved_tool_dir: Path, inputs: dict[str, str]):
        captured["tool_dir"] = resolved_tool_dir
        captured["inputs"] = inputs
        return ToolRunResult(output="ok", error="", elapsed_ms=1.0, exit_code=0)

    monkeypatch.setattr(run_module, "validate_yaml_file", fake_validate_yaml_file)
    monkeypatch.setattr(run_module, "run_tool", fake_run_tool)

    result = run_module.run_skill(ws, "csv-cleaner", {"input_path": "examples/input.csv"})

    assert result.exit_code == 0
    assert captured["tool_dir"] == tool_dir
    assert captured["yaml_path"] == tool_dir / "toolforge.yaml"


def test_run_skill_normalizes_relative_output_path(monkeypatch, ws: Path):
    captured: dict[str, object] = {}
    tool_dir = _write_generated_tool(ws, "csv-cleaner")

    def fake_validate_yaml_file(path: Path):
        captured["yaml_path"] = path
        return _DummySpec()

    def fake_run_tool(spec, resolved_tool_dir: Path, inputs: dict[str, str]):
        captured["inputs"] = inputs
        return ToolRunResult(output="ok", error="", elapsed_ms=1.0, exit_code=0)

    monkeypatch.setattr(run_module, "validate_yaml_file", fake_validate_yaml_file)
    monkeypatch.setattr(run_module, "run_tool", fake_run_tool)

    result = run_module.run_skill(
        ws,
        "csv-cleaner",
        {"output_path": "outputs/csv-cleaner-output.json"},
    )

    assert result.exit_code == 0
    assert captured["inputs"] == {
        "output_path": str((ws / "outputs" / "csv-cleaner-output.json").resolve())
    }


def test_run_skill_error_lists_checked_paths(ws: Path):
    with pytest.raises(FileNotFoundError) as exc_info:
        run_module.run_skill(ws, "csv-cleaner", {})

    message = str(exc_info.value)
    assert "Could not resolve tool for skill 'csv-cleaner'." in message
    assert "registry entrypoint" in message
    assert "skills/csv-cleaner/tool" in message
    assert "tools/generated/csv-cleaner" in message


def test_run_skill_requires_registered_skill(tmp_path: Path):
    with pytest.raises(ValueError):
        run_module.run_skill(tmp_path, "csv-cleaner", {})
