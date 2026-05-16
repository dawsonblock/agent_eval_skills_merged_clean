"""
runner_bridge — run toolathlon task scenarios through ToolForge eval runner.
"""
from __future__ import annotations

from pathlib import Path

from packages.core.tool_spec import EvalSpec, ToolSpec
from packages.integrations.toolathlon.task_adapter import load_eval_cases_from_dir
from packages.runners.eval_runner import EvalReport, run_evals


def run_toolathlon_tasks(
    spec: ToolSpec,
    tool_dir: Path,
    tasks_dir: Path,
    timeout_s: float = 30.0,
) -> EvalReport:
    """
    Load toolathlon task JSONs from *tasks_dir*, inject them into *spec.eval*,
    and run the full eval suite via ToolForge's eval runner.

    Returns an EvalReport with results for every loaded task.
    """
    cases = load_eval_cases_from_dir(tasks_dir)

    # Build an ephemeral EvalSpec using the loaded cases
    eval_spec = EvalSpec(
        enabled=True,
        cases=cases,
        criteria=spec.eval.criteria if spec.eval else [],
        baseline_pass_rate=spec.eval.baseline_pass_rate if spec.eval else 0.8,
    )

    patched_spec = spec.model_copy(update={"eval": eval_spec})
    return run_evals(patched_spec, tool_dir, timeout_s=timeout_s)
