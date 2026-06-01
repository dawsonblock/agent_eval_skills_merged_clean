"""
task_adapter — convert toolathlon task definitions into ToolForge EvalCase objects.
"""

from __future__ import annotations

import json
from pathlib import Path

from packages.core.tool_spec import EvalCase


def load_toolathlon_task(task_path: Path) -> dict:
    """Load a toolathlon task JSON or YAML and return as dict."""
    text = task_path.read_text(encoding="utf-8")
    if task_path.suffix in (".yaml", ".yml"):
        import yaml  # noqa: PLC0415

        return yaml.safe_load(text)
    return json.loads(text)


def task_to_eval_cases(task: dict, idx: int = 0) -> list[EvalCase]:
    """
    Convert a single toolathlon task dict into a list of ToolForge EvalCase objects.

    Expected toolathlon task structure::
      {
        "task_id": "...",
        "description": "...",
        "inputs": {...},
        "expected_output": "...",
        "tags": [...]
      }
    """
    task_id = str(task.get("task_id") or f"task-{idx:04d}")
    inputs = task.get("inputs") or {}
    expected_output = task.get("expected_output")
    tags = list(task.get("tags", []))
    description = task.get("description", "")

    return [
        EvalCase(
            id=task_id,
            description=description,
            inputs=inputs,
            expected_output=str(expected_output) if expected_output is not None else None,
            tags=tags,
        )
    ]


def load_eval_cases_from_dir(tasks_dir: Path) -> list[EvalCase]:
    """
    Walk *tasks_dir* and aggregate all toolathlon tasks into EvalCase objects.
    """
    cases: list[EvalCase] = []
    for idx, task_file in enumerate(sorted(tasks_dir.rglob("*.json"))):
        task = load_toolathlon_task(task_file)
        cases.extend(task_to_eval_cases(task, idx=idx))
    return cases
