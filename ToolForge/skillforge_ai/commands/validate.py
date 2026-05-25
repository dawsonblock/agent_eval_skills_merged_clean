from __future__ import annotations
# mypy: disable-error-code=import-untyped

from pathlib import Path

from skillforge_ai.evidence_logger import EvidenceLogger
from skillforge_ai.validation_runner import ValidationRunner


def run_validate(workspace_root: Path, slug: str, repair: bool, provider: str):
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
    evidence.finalize()
    return report
