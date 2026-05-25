from __future__ import annotations
# mypy: disable-error-code=import-untyped

import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
import time

from packages.runners.tool_runner import run_tool
from packages.runners.tool_runner import ToolRunResult
from packages.validators.schema_validator import validate_yaml_file
from skillforge_ai.evidence_logger import EvidenceLogger
from skillforge_ai.models import ToolCallRequest
from skillforge_ai.permissions import PermissionBroker
from skillforge_ai.skill_registry import SkillRegistry
from skillforge_ai.tool_registry import SkillForgeRegistry


def run_skill(workspace_root: Path, slug: str, inputs: dict[str, str]):
    root = workspace_root.resolve()
    evidence = EvidenceLogger(
        log_dir=root / ".skillforge" / "evidence", skill_name=slug
    )
    broker = PermissionBroker(interactive=False, auto_approve=True)
    broker.check("read_local_files")
    broker.check("write_files")

    registry = SkillRegistry(root)
    skill_entry = registry.get(slug)
    if skill_entry is None:
        raise ValueError(
            f"Skill '{slug}' is not registered. Register or install it before running."
        )

    tool_dir, entrypoint_path, checked = _resolve_tool_location(
        root, slug, skill_entry
    )
    if tool_dir is None:
        checked_lines = "\n".join(f"- {line}" for line in checked)
        raise FileNotFoundError(
            f"Could not resolve tool for skill '{slug}'.\nChecked:\n{checked_lines}"
        )

    normalized_inputs = _normalize_inputs_for_workspace(root, inputs)
    evidence.log_message("run_request", skill=slug, inputs=normalized_inputs)

    yaml_path = tool_dir / "toolforge.yaml"
    if yaml_path.exists():
        spec = validate_yaml_file(yaml_path)
        result = run_tool(spec, tool_dir, normalized_inputs)
    else:
        result = _run_python_entrypoint(
            tool_dir, entrypoint_path, normalized_inputs
        )

    evidence.log_tool_call(
        ToolCallRequest(
            tool="local_python",
            action="run_skill",
            arguments={
                "skill": slug,
                "tool_dir": str(tool_dir),
                "inputs": normalized_inputs,
            },
            permissions_required=["read_local_files", "write_files"],
        ),
        {
            "exit_code": result.exit_code,
            "stdout": result.output,
            "stderr": result.error,
        },
        success=result.exit_code == 0,
    )

    skill_entry["last_run"] = datetime.now(timezone.utc).isoformat()
    registry.upsert(skill_entry)

    evidence.write_minimum_artifacts(
        run_payload={
            "event": "run",
            "skill": slug,
            "status": "passed" if result.exit_code == 0 else "failed",
            "exit_code": result.exit_code,
            "ts": datetime.now(timezone.utc).isoformat(),
        },
        files_changed=[],
        validation_payload={
            "skill": slug,
            "status": "passed" if result.exit_code == 0 else "failed",
            "errors": [result.error] if result.error else [],
            "warnings": [],
            "ts": datetime.now(timezone.utc).isoformat(),
        },
    )
    evidence.finalize()
    return result


def _resolve_tool_location(
    root: Path,
    slug: str,
    skill_entry: dict[str, object],
) -> tuple[Path | None, Path | None, list[str]]:
    checked: list[str] = []
    tool_registry = SkillForgeRegistry(root)

    registry_tool = tool_registry.get_registered_tool(
        f"{slug}_tool"
    ) or tool_registry.get_registered_tool(slug)
    if registry_tool is None:
        checked.append("registry entrypoint: missing")
    else:
        registry_entrypoint = _to_abs_path(
            root, registry_tool.get("entrypoint")
        )
        registry_working_dir = _to_abs_path(
            root, registry_tool.get("working_dir")
        )
        if registry_working_dir is None and registry_entrypoint is not None:
            registry_working_dir = registry_entrypoint.parent
        registry_entrypoint_label = (
            str(registry_entrypoint)
            if registry_entrypoint is not None
            else "missing"
        )
        checked.append(
            f"registry entrypoint: {registry_entrypoint_label}"
        )
        if registry_working_dir is not None and registry_working_dir.exists():
            return registry_working_dir, registry_entrypoint, checked

    skill_tool_path = _to_abs_path(root, skill_entry.get("tool_path"))
    if skill_tool_path is None:
        skill_tool_path = _to_abs_path(root, skill_entry.get("path"))
    if skill_tool_path is not None and skill_tool_path.name != "tool":
        candidate = skill_tool_path / "tool"
        if candidate.exists():
            skill_tool_path = candidate
    checked.append(
        f"skill registry tool path: {skill_tool_path if skill_tool_path is not None else 'missing'}"
    )
    if skill_tool_path is not None and skill_tool_path.exists():
        return skill_tool_path, None, checked

    skill_local_tool = root / "skills" / slug / "tool"
    checked.append(f"skills/{slug}/tool: {skill_local_tool}")
    if skill_local_tool.exists():
        return skill_local_tool, None, checked

    generated_tool = root / "tools" / "generated" / slug
    checked.append(f"tools/generated/{slug}: {generated_tool}")
    if generated_tool.exists():
        return generated_tool, None, checked

    return None, None, checked


def _to_abs_path(root: Path, value: object) -> Path | None:
    if not isinstance(value, str) or not value.strip():
        return None
    path = Path(value)
    if path.is_absolute():
        return path
    return (root / path).resolve()


def _normalize_inputs_for_workspace(
    root: Path, inputs: dict[str, str]
) -> dict[str, str]:
    normalized: dict[str, str] = {}
    for key, value in inputs.items():
        raw = str(value)
        path_candidate = Path(raw)
        if not path_candidate.is_absolute():
            workspace_candidate = (root / path_candidate).resolve()
            if workspace_candidate.exists():
                normalized[key] = str(workspace_candidate)
                continue
        normalized[key] = raw
    return normalized


def _run_python_entrypoint(
    tool_dir: Path,
    entrypoint_path: Path | None,
    inputs: dict[str, str],
) -> ToolRunResult:
    entrypoint = entrypoint_path
    if entrypoint is None:
        for candidate in (tool_dir / "main.py", tool_dir / "tool.py"):
            if candidate.exists():
                entrypoint = candidate
                break
    if entrypoint is None or not entrypoint.exists():
        return ToolRunResult(
            output="",
            error=f"Entry point not found in {tool_dir}",
            elapsed_ms=0.0,
            exit_code=1,
        )

    command = [sys.executable, str(entrypoint)]
    env = dict(os.environ)
    env.update({"TOOLFORGE_INPUTS": json.dumps(inputs)})
    start = time.monotonic()
    try:
        completed = subprocess.run(
            command,
            cwd=tool_dir,
            capture_output=True,
            text=True,
            env=env,
            timeout=30,
        )
    except subprocess.TimeoutExpired as exc:
        elapsed_ms = (time.monotonic() - start) * 1000
        return ToolRunResult(
            output=exc.stdout or "",
            error=exc.stderr or "Tool execution timed out",
            elapsed_ms=elapsed_ms,
            exit_code=1,
        )
    elapsed_ms = (time.monotonic() - start) * 1000
    return ToolRunResult(
        output=completed.stdout,
        error=completed.stderr,
        elapsed_ms=elapsed_ms,
        exit_code=completed.returncode,
    )
