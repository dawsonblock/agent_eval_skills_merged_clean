"""Tests for expected failure semantics in eval runner."""
from __future__ import annotations

from pathlib import Path

from packages.core.tool_spec import (
    EvalCase,
    EvalSpec,
    ParameterSpec,
    SecuritySpec,
    ToolLanguage,
    ToolSpec,
)
from packages.runners.eval_runner import run_evals


def _spec() -> ToolSpec:
    return ToolSpec(
        name="CSV Cleaner",
        slug="csv-cleaner",
        version="0.1.0",
        description="CSV cleaner",
        language=ToolLanguage.PYTHON,
        entry_point="tool.py",
        parameters=[
            ParameterSpec(name="input_path", type="string", description="input"),
            ParameterSpec(
                name="output_path",
                type="string",
                description="output",
                required=False,
                default="outputs/cleaned.csv",
            ),
        ],
        security=SecuritySpec(
            requires_filesystem=True,
            allowed_read_paths=["./examples/**"],
            allowed_write_paths=["./outputs/**"],
            allowed_extensions=[".csv"],
        ),
        eval=EvalSpec(
            enabled=True,
            baseline_pass_rate=1.0,
            cases=[
                EvalCase(
                    id="case-01-success",
                    description="success",
                    inputs={"input_path": "examples/input.csv"},
                    expected_success=True,
                    expected_output_contains="cleaned_path",
                ),
                EvalCase(
                    id="case-02-safety",
                    description="blocked",
                    inputs={"input_path": "../../../etc/passwd"},
                    expected_success=False,
                    expected_error_contains="Path validation failed",
                ),
            ],
        ),
    )


def _tool_code() -> str:
    return """from __future__ import annotations
import json
import os
from pathlib import Path

def run(input_path: str, output_path: str | None = None) -> dict:
    src = Path(input_path)
    out = Path(output_path or 'outputs/cleaned.csv')
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text('name\\nAlice\\n', encoding='utf-8')
    return {'cleaned_path': str(out)}

if __name__ == '__main__':
    inputs = json.loads(os.environ['TOOLFORGE_INPUTS'])
    print(json.dumps(run(**inputs)))
"""


def test_expected_failure_case_passes_when_blocked(tmp_path: Path) -> None:
    tool_dir = tmp_path / "csv-cleaner"
    (tool_dir / "examples").mkdir(parents=True)
    (tool_dir / "examples" / "input.csv").write_text("name\nAlice\n", encoding="utf-8")
    (tool_dir / "tool.py").write_text(_tool_code(), encoding="utf-8")

    report = run_evals(_spec(), tool_dir)

    by_id = {r.case_id: r for r in report.results}
    assert by_id["case-01-success"].passed
    assert by_id["case-02-safety"].passed
    assert report.overall_pass
