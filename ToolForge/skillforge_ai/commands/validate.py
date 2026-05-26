from __future__ import annotations
# mypy: disable-error-code=import-untyped

import json
from datetime import datetime, timezone
from pathlib import Path

from skillforge_ai.evidence_logger import EvidenceLogger
from skillforge_ai.validation_runner import ValidationRunner


def _write_validation_summary(
    output_path: Path,
    workspace_root: Path,
    slug: str,
    repair: bool,
    provider: str,
    report,
) -> None:
    payload = {
        "summary_version": "2026-05-25",
        "component": "skillforge_ai",
        "artifact_type": "validation_summary",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "workspace": str(workspace_root),
        "skill": slug,
        "repair": repair,
        "provider": provider,
        "overall_status": "passed" if report.passed else "failed",
        "checks": {
            "schema": "passed" if report.schema_ok else "failed",
            "security": "passed" if report.security_ok else "failed",
            "mcp": (
                "not_run"
                if report.mcp_ok is None
                else ("passed" if report.mcp_ok else "failed")
            ),
            "skill": "passed" if report.skill_ok else "failed",
            "tests": "passed" if report.tests_ok else "failed",
            "safety": "passed" if report.safety_ok else "failed",
        },
        "attempt": report.attempt,
        "errors": report.errors,
        "warnings": report.warnings,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )


def run_validate(
    workspace_root: Path,
    slug: str,
    repair: bool,
    provider: str,
    summary_json: Path | None = None,
):
    evidence = EvidenceLogger(
        log_dir=workspace_root / ".skillforge" / "evidence",
        skill_name=slug,
    )
    runner = ValidationRunner(
        workspace_root=workspace_root, evidence_logger=evidence
    )
    report = (
        runner.repair_loop(slug, provider=provider)
        if repair
        else runner.validate(slug)
    )
    evidence.write_minimum_artifacts(
        run_payload={
            "event": "validate",
            "skill": slug,
            "status": "passed" if report.passed else "failed",
            "repair": repair,
        },
        files_changed=[
            str(workspace_root / "skills" / slug / "validation_report.json")
        ],
        validation_payload={
            "skill": slug,
            "status": "passed" if report.passed else "failed",
            "errors": report.errors,
            "warnings": report.warnings,
        },
    )
    if summary_json is not None:
        _write_validation_summary(
            output_path=summary_json,
            workspace_root=workspace_root,
            slug=slug,
            repair=repair,
            provider=provider,
            report=report,
        )
    evidence.finalize()
    return report
