from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from skillforge_ai.validation_runner import ValidationRunner


@dataclass
class RepairAttempt:
    attempt: int
    category: str
    summary: str


class RepairLoop:
    def __init__(self, workspace_root: Path, max_attempts: int = 3) -> None:
        self._runner = ValidationRunner(workspace_root=workspace_root, max_repair_attempts=max_attempts)
        self._max_attempts = max_attempts

    def run(self, slug: str, provider: str = "rule_based") -> tuple[bool, list[RepairAttempt]]:
        attempts: list[RepairAttempt] = []
        report = self._runner.validate(slug, attempt=1)
        attempts.append(RepairAttempt(1, self._classify(report.errors), self._summarize(report.errors)))

        if report.passed:
            return True, attempts

        for idx in range(2, self._max_attempts + 1):
            report = self._runner.repair_loop(slug, provider=provider)
            attempts.append(RepairAttempt(idx, self._classify(report.errors), self._summarize(report.errors)))
            if report.passed:
                return True, attempts
        return False, attempts

    @staticmethod
    def _classify(errors: list[str]) -> str:
        text = " ".join(errors).lower()
        if "schema" in text:
            return "schema_error"
        if "missing" in text:
            return "missing_file"
        if "test" in text:
            return "test_failure"
        if "mcp" in text:
            return "mcp_startup_error"
        if "permission" in text:
            return "permission_error"
        if "syntax" in text:
            return "syntax_error"
        return "tool_runtime_error"

    @staticmethod
    def _summarize(errors: list[str]) -> str:
        if not errors:
            return "No validation errors"
        return "; ".join(errors[:3])
