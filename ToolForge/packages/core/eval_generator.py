"""
Eval generator — renders an eval task directory from a ToolSpec.

Creates:
  evals/generated/{slug}/
    ├── task_config.json      (task metadata for Toolathlon-style runner)
    ├── agent_system_prompt.md
    ├── evaluation.py         (evaluator script)
    └── cases/
        └── {case.id}.json    (one JSON file per eval case)
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from packages.core.tool_spec import ToolSpec
from packages.core.generator_utils import render_template, write_rendered, TOOLFORGE_VERSION


def generate_eval(spec: ToolSpec, output_root: Path, overwrite: bool = False) -> list[Path]:
    """
    Generate an eval task directory for *spec* under *output_root/{spec.slug}/*.
    """
    if output_root.name == "evals":
        eval_dir = output_root
    else:
        eval_dir = output_root / spec.slug
    eval_dir.mkdir(parents=True, exist_ok=True)
    (eval_dir / "cases").mkdir(exist_ok=True)

    ctx: dict[str, Any] = {
        "spec": spec,
        "toolforge_version": TOOLFORGE_VERSION,
        "task_description": f"Use the {spec.slug} tool to complete the assigned task.",
    }
    written: list[Path] = []

    # task_config.json
    cfg = render_template("eval_task_template", "task_config.json.j2", ctx)
    if write_rendered(eval_dir / "task_config.json", cfg, overwrite):
        written.append(eval_dir / "task_config.json")

    # agent_system_prompt.md
    prompt = render_template("eval_task_template", "agent_system_prompt.md.j2", ctx)
    if write_rendered(eval_dir / "agent_system_prompt.md", prompt, overwrite):
        written.append(eval_dir / "agent_system_prompt.md")

    # evaluation.py
    evaluator = render_template("eval_task_template", "evaluation.py.j2", ctx)
    if write_rendered(eval_dir / "evaluation.py", evaluator, overwrite):
        written.append(eval_dir / "evaluation.py")

    # Individual case files
    for case in spec.eval.cases:
        case_file = eval_dir / "cases" / f"{case.id}.json"
        case_data = case.model_dump(exclude_none=True)
        if write_rendered(case_file, json.dumps(case_data, indent=2) + "\n", overwrite):
            written.append(case_file)

    return written
