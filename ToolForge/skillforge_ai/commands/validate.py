from __future__ import annotations

from pathlib import Path

from skillforge_ai.evidence_logger import EvidenceLogger
from skillforge_ai.validation_runner import ValidationRunner


def run_validate(workspace_root: Path, slug: str, repair: bool, provider: str):
    evidence = EvidenceLogger(
        log_dir=workspace_root / ".skillforge" / "evidence",
        skill_name=slug,
    )
    runner = ValidationRunner(workspace_root=workspace_root, evidence_logger=evidence)
    report = runner.repair_loop(slug, provider=provider) if repair else runner.validate(slug)
    evidence.finalize()
    return report
