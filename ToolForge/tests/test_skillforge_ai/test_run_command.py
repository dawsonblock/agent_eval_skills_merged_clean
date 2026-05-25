from __future__ import annotations

from pathlib import Path

import pytest

from packages.runners.tool_runner import ToolRunResult
from skillforge_ai.commands import run as run_module


class _DummySpec:
    entry_point = "tool.py"


def test_run_skill_resolves_workspace_root(monkeypatch):
    captured: dict[str, object] = {}

    def fake_validate_yaml_file(path: Path):
        captured["yaml_path"] = path
        return _DummySpec()

    def fake_run_tool(spec, tool_dir: Path, inputs: dict[str, str]):
        captured["tool_dir"] = tool_dir
        captured["inputs"] = inputs
        return ToolRunResult(output="ok", error="", elapsed_ms=1.0, exit_code=0)

    monkeypatch.setattr(run_module, "validate_yaml_file", fake_validate_yaml_file)
    monkeypatch.setattr(run_module, "run_tool", fake_run_tool)

    result = run_module.run_skill(Path("."), "csv-cleaner", {"input_path": "examples/input.csv"})

    assert result.exit_code == 0
    assert isinstance(captured["tool_dir"], Path)
    assert captured["tool_dir"].is_absolute()


def test_run_skill_requires_registered_skill(tmp_path: Path):
    with pytest.raises(ValueError):
        run_module.run_skill(tmp_path, "csv-cleaner", {})
