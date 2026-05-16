"""Unit tests for packages.core.eval_generator."""
from __future__ import annotations

import json
from pathlib import Path

from packages.core.eval_generator import generate_eval
from packages.core.tool_spec import (
    EvalCase,
    EvalCriterion,
    EvalCriterionType,
    EvalSpec,
    ToolLanguage,
    ToolSpec,
)


def _make_spec() -> ToolSpec:
    return ToolSpec(
        name="Eval Tool",
        slug="eval-tool",
        version="0.1.0",
        description="A tool with eval",
        language=ToolLanguage.PYTHON,
        entry_point="tool.py",
        eval=EvalSpec(
            enabled=True,
            cases=[
                EvalCase(id="case-01", inputs={"x": "hello"}, description="Smoke test"),
            ],
            criteria=[
                EvalCriterion(name="no_error", type=EvalCriterionType.NO_ERROR, weight=1.0),
            ],
        ),
    )


def test_generates_cases_dir(tmp_path: Path) -> None:
    spec = _make_spec()
    created = generate_eval(spec, tmp_path)
    dirs = {p.parent.name for p in created}
    assert "cases" in dirs


def test_generates_task_config(tmp_path: Path) -> None:
    spec = _make_spec()
    created = generate_eval(spec, tmp_path)
    names = {p.name for p in created}
    assert "task_config.json" in names


def test_task_config_valid_json(tmp_path: Path) -> None:
    spec = _make_spec()
    created = generate_eval(spec, tmp_path)
    cfg_file = next(p for p in created if p.name == "task_config.json")
    data = json.loads(cfg_file.read_text(encoding="utf-8"))
    assert "slug" in data or "tool_slug" in data or "name" in data


def test_eval_case_file_created(tmp_path: Path) -> None:
    spec = _make_spec()
    created = generate_eval(spec, tmp_path)
    # At least one case file should exist
    case_files = [p for p in created if "case" in p.name.lower()]
    assert len(case_files) >= 1
