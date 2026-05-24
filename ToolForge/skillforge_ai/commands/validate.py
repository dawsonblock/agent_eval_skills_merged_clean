from __future__ import annotations

from pathlib import Path

from skillforge_ai.validation_runner import ValidationRunner


def run_validate(workspace_root: Path, slug: str) -> dict:
    report = ValidationRunner(workspace_root=workspace_root).validate(slug)
    return {
        "skill": slug,
        "status": "passed" if report.passed else "failed",
        "checks": {
            "metadata": "passed" if report.schema_ok else "failed",
            "skill_md": "passed" if report.skill_ok else "failed",
            "syntax": "passed" if report.schema_ok else "failed",
            "tests": "passed" if report.tests_ok else "failed",
            "package": "passed" if report.safety_ok else "failed",
        },
        "errors": report.errors,
    }
