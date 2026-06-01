from __future__ import annotations
# mypy: disable-error-code=import-untyped

from pathlib import Path
from typing import Any
import json

from skillforge_ai.evidence_logger import EvidenceLogger
from skillforge_ai.planner import SkillPlanner
from skillforge_ai.skill_builder import SkillBuilder
from skillforge_ai.skill_registry import SkillRegistry
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
    tool_dir, manifest = builder.build(
        prompt, skill_name=name or plan.skill_name
    )

    skillforge_registry = SkillForgeRegistry(workspace_root)
    skillforge_registry.register_skill(manifest, tool_dir)

    relative_skill_path = Path("skills") / manifest.name
    relative_tool_path = relative_skill_path / "tool"
    skill_registry = SkillRegistry(workspace_root)
    skill_registry.upsert(
        {
            "name": manifest.name,
            "path": str(relative_skill_path),
            "category": manifest.category,
            "description": manifest.description,
            "permissions": manifest.permissions,
            "risk_level": manifest.risk_level,
            "validation_status": "created",
            "tool_refs": [f"{manifest.name.replace('-', '_')}_tool"],
            "package_hash": None,
            "last_run": None,
        }
    )

    skillforge_registry.register_tool(
        {
            "name": f"{manifest.name.replace('-', '_')}_tool",
            "type": "python",
            "entrypoint": str(relative_tool_path / "main.py"),
            "working_dir": str(relative_tool_path),
            "description": manifest.description,
            "permissions": manifest.permissions
            or ["read_files", "write_files"],
            "risk_level": manifest.risk_level,
            "validated": False,
            "mcp_server": None,
        }
    )

    _validate_generated_metadata_schema(workspace_root, manifest.name)
    evidence.log_message("plan", plan=plan.to_dict())
    evidence.write_minimum_artifacts(
        run_payload={
            "event": "create",
            "skill": manifest.name,
            "status": "passed",
            "prompt": prompt,
        },
        files_changed=[
            str(tool_dir),
            str(workspace_root / "skills" / manifest.name),
        ],
        validation_payload={
            "skill": manifest.name,
            "status": "passed",
            "errors": [],
            "warnings": [],
        },
    )
    evidence.finalize()
    return tool_dir, manifest


def _validate_generated_metadata_schema(
    workspace_root: Path, skill_name: str
) -> None:
    from jsonschema import validate

    schema_path = (
        Path(__file__).resolve().parent.parent
        / "schemas"
        / "skill_schema.json"
    )
    metadata_path = workspace_root / "skills" / skill_name / "metadata.json"

    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    payload = json.loads(metadata_path.read_text(encoding="utf-8"))
    validate(instance=payload, schema=schema)
