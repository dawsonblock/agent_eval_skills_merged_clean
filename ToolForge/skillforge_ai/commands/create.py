from __future__ import annotations

from pathlib import Path
from typing import Any
import json

from skillforge_ai.evidence_logger import EvidenceLogger
from skillforge_ai.planner import SkillPlanner
from skillforge_ai.skill_builder import SkillBuilder
from skillforge_ai.tool_registry import SkillForgeRegistry


def run_create(
    workspace_root: Path,
    prompt: str,
    provider: str = "rule_based",
    name: str | None = None,
    generate_mcp: bool = True,
    generate_eval_harness: bool = True,
) -> tuple[Path, Any]:
    planner = SkillPlanner()
    plan = planner.build_plan(prompt)
    evidence = EvidenceLogger(
        log_dir=workspace_root / ".skillforge" / "evidence",
        skill_name=name or plan.skill_name,
    )
    builder = SkillBuilder(
        workspace_root=workspace_root,
        provider=provider,
        evidence_logger=evidence,
        generate_mcp=generate_mcp,
        generate_eval_harness=generate_eval_harness,
    )
    tool_dir, manifest = builder.build(prompt, skill_name=name or plan.skill_name)

    SkillForgeRegistry(workspace_root).register_skill(manifest, tool_dir)
    _validate_generated_metadata_schema(workspace_root, manifest.name)
    evidence.log_message("plan", plan=plan.to_dict())
    evidence.finalize()
    return tool_dir, manifest


def _validate_generated_metadata_schema(workspace_root: Path, skill_name: str) -> None:
    from jsonschema import validate

    schema_path = workspace_root / "skillforge_ai" / "schemas" / "skill_schema.json"
    metadata_path = workspace_root / "skills" / skill_name / "metadata.json"

    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    payload = json.loads(metadata_path.read_text(encoding="utf-8"))
    validate(instance=payload, schema=schema)
