"""Tests for eval case source-of-truth loading."""
from __future__ import annotations

import json
from pathlib import Path

from packages.core.tool_spec import EvalCase, EvalSpec, ParameterSpec, ToolLanguage, ToolSpec
from packages.runners.eval_runner import run_evals


def _make_spec() -> ToolSpec:
    return ToolSpec(
        name="Echo Tool",
        slug="echo-tool",
        version="0.1.0",
        description="Echo tool",
        language=ToolLanguage.PYTHON,
        entry_point="tool.py",
        parameters=[ParameterSpec(name="input", type="string", description="input")],
        eval=EvalSpec(
            enabled=True,
            baseline_pass_rate=1.0,
            cases=[
                EvalCase(
                    id="yaml-case",
                    description="yaml fallback case",
                    inputs={"input": "from-yaml"},
                    expected_success=True,
                    expected_output_contains="echo:from-yaml",
                )
            ],
        ),
    )


def _write_echo_tool(tool_dir: Path) -> None:
    tool_dir.mkdir(parents=True, exist_ok=True)
    (tool_dir / "tool.py").write_text(
        """from __future__ import annotations
import json
import os


def run(input: str) -> str:
    return f\"echo:{input}\"


if __name__ == \"__main__\":
    inputs = json.loads(os.environ[\"TOOLFORGE_INPUTS\"])
    print(run(**inputs))
""",
        encoding="utf-8",
    )


def test_eval_prefers_tool_local_case_files(tmp_path: Path) -> None:
    spec = _make_spec()
    tool_dir = tmp_path / "echo-tool"
    _write_echo_tool(tool_dir)

    case_dir = tool_dir / "evals" / "cases"
    case_dir.mkdir(parents=True)
    (case_dir / "file-case.json").write_text(
        json.dumps(
            {
                "id": "file-case",
                "description": "file-sourced case",
                "inputs": {"input": "from-file"},
                "expected_success": True,
                "expected_output_contains": "echo:from-file",
            }
        ),
        encoding="utf-8",
    )

    report = run_evals(spec, tool_dir)

    by_id = {r.case_id: r for r in report.results}
    assert "file-case" in by_id
    assert by_id["file-case"].passed
    assert "yaml-case" not in by_id


def test_eval_falls_back_to_yaml_cases_when_files_missing(tmp_path: Path) -> None:
    spec = _make_spec()
    tool_dir = tmp_path / "echo-tool"
    _write_echo_tool(tool_dir)

    report = run_evals(spec, tool_dir)

    by_id = {r.case_id: r for r in report.results}
    assert "yaml-case" in by_id
    assert by_id["yaml-case"].passed
