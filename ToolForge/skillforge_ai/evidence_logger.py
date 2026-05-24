"""
EvidenceLogger — append-only structured audit trail for SkillForge AI sessions.

All AI-driven actions (builds, validations, repairs, tool calls, approvals,
package hashes) are recorded as JSON objects in a per-session JSONL file:

    .skillforge/evidence/{YYYYMMDD_HHMMSS}_{skill}.jsonl

At session end, call finalize() to write a session_summary.json.
"""
from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from skillforge_ai.models import ApprovalRequest, ToolCallRequest, ValidationReport

logger = logging.getLogger(__name__)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sha256(path: Path) -> str | None:
    """Return SHA-256 hex digest of a file, or None if the file doesn't exist."""
    if not path.exists():
        return None
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


class EvidenceLogger:
    """
    Write structured evidence records to a JSONL file.

    Usage::

        with EvidenceLogger(Path(".skillforge/evidence"), "csv-cleaner") as ev:
            ev.log_build("csv-cleaner", files_created=[...], spec={...})
            ev.log_validation("csv-cleaner", report)
            ev.log_tool_call(request, result)
        # finalize() called automatically on context exit
    """

    def __init__(self, log_dir: Path, skill_name: str = "session") -> None:
        self._log_dir = log_dir
        self._log_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        safe_name = skill_name.replace("/", "_").replace(" ", "_")
        self._run_dir = log_dir / "runs" / f"{stamp}_{safe_name}"
        self._run_dir.mkdir(parents=True, exist_ok=True)
        self._run_json = self._run_dir / "run.json"
        self._files_changed_json = self._run_dir / "files_changed.json"
        self._validation_json = self._run_dir / "validation.json"
        self._log_path = log_dir / f"{stamp}_{safe_name}.jsonl"
        self._summary_path = log_dir / f"{stamp}_{safe_name}_summary.json"
        self._counts: dict[str, int] = {
            "builds": 0,
            "validations": 0,
            "repairs": 0,
            "tool_calls": 0,
            "commands": 0,
            "approvals": 0,
            "packages": 0,
        }
        self._errors: list[str] = []
        self._packages: list[dict[str, str]] = []
        self._latest_run: dict[str, Any] = {
            "skill": skill_name,
            "started_at": _now_iso(),
            "events": [],
        }

    # ------------------------------------------------------------------
    # Context manager
    # ------------------------------------------------------------------

    def __enter__(self) -> "EvidenceLogger":
        return self

    def __exit__(self, *_) -> None:
        self.finalize()

    # ------------------------------------------------------------------
    # Logging helpers
    # ------------------------------------------------------------------

    def _write(self, record: dict[str, Any]) -> None:
        record.setdefault("ts", _now_iso())
        self._latest_run["events"].append(record)
        try:
            with self._log_path.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(record, default=str) + "\n")
        except OSError as exc:
            logger.warning("EvidenceLogger: could not write to %s: %s", self._log_path, exc)

    def _write_artifact(self, path: Path, payload: dict[str, Any]) -> None:
        try:
            path.write_text(
                json.dumps(payload, indent=2, default=str) + "\n",
                encoding="utf-8",
            )
        except OSError as exc:
            logger.warning("EvidenceLogger: could not write artifact %s: %s", path, exc)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def log_build(
        self,
        skill_name: str,
        files_created: list[Path | str],
        spec: dict[str, Any] | None = None,
    ) -> None:
        """Record a skill build event."""
        self._counts["builds"] += 1
        self._write({
            "event": "build",
            "skill": skill_name,
            "files_created": [str(f) for f in files_created],
            "spec_summary": {
                "name": spec.get("name") if spec else None,
                "language": spec.get("language") if spec else None,
            },
        })
        self._write_artifact(
            self._run_json,
            {
                "skill": skill_name,
                "event": "build",
                "ts": _now_iso(),
                "spec_summary": {
                    "name": spec.get("name") if spec else None,
                    "language": spec.get("language") if spec else None,
                },
            },
        )
        self._write_artifact(
            self._files_changed_json,
            {
                "skill": skill_name,
                "files_changed": [str(f) for f in files_created],
                "ts": _now_iso(),
            },
        )

    def log_validation(
        self,
        skill_name: str,
        report: ValidationReport,
    ) -> None:
        """Record a validation run."""
        self._counts["validations"] += 1
        if not report.passed:
            self._errors.extend(report.errors)
        self._write({
            "event": "validation",
            "skill": skill_name,
            "attempt": report.attempt,
            "passed": report.passed,
            "errors": report.errors,
            "warnings": report.warnings,
            "validators": {
                "schema": report.schema_ok,
                "security": report.security_ok,
                "mcp": report.mcp_ok,
                "skill": report.skill_ok,
                "tests": report.tests_ok,
                "safety": report.safety_ok,
            },
        })
        self._write_artifact(
            self._validation_json,
            {
                "skill": skill_name,
                "attempt": report.attempt,
                "status": "passed" if report.passed else "failed",
                "errors": report.errors,
                "warnings": report.warnings,
                "validators": {
                    "schema": report.schema_ok,
                    "security": report.security_ok,
                    "mcp": report.mcp_ok,
                    "skill": report.skill_ok,
                    "tests": report.tests_ok,
                    "safety": report.safety_ok,
                },
            },
        )

    def log_repair(
        self,
        skill_name: str,
        error_summary: str,
        patch_description: str,
        attempt: int,
        file_patched: str | None = None,
    ) -> None:
        """Record an AI repair attempt."""
        self._counts["repairs"] += 1
        self._write({
            "event": "repair",
            "skill": skill_name,
            "attempt": attempt,
            "error_summary": error_summary,
            "patch_description": patch_description,
            "file_patched": file_patched,
        })

    def log_tool_call(
        self,
        request: ToolCallRequest,
        result: Any,
        success: bool = True,
    ) -> None:
        """Record a tool/MCP call and its result."""
        self._counts["tool_calls"] += 1
        self._write({
            "event": "tool_call",
            "tool": request.tool,
            "action": request.action,
            "arguments": request.arguments,
            "permissions_required": request.permissions_required,
            "approval_required": request.approval_required,
            "success": success,
            "result_summary": str(result)[:500] if result is not None else None,
        })

    def log_command(
        self,
        cmd: list[str],
        returncode: int,
        stdout: str,
        stderr: str,
    ) -> None:
        """Record a subprocess command execution."""
        self._counts["commands"] += 1
        self._write({
            "event": "command",
            "cmd": cmd,
            "returncode": returncode,
            "stdout_tail": stdout[-500:] if stdout else "",
            "stderr_tail": stderr[-500:] if stderr else "",
            "success": returncode == 0,
        })

    def log_approval(self, request: ApprovalRequest) -> None:
        """Record an approval decision."""
        self._counts["approvals"] += 1
        self._write({
            "event": "approval",
            "step_id": request.step.step_id,
            "action": request.step.action,
            "risk_level": request.step.risk_level,
            "reason": request.reason,
            "approved": request.approved,
        })

    def log_package(
        self,
        skill_name: str,
        zip_path: Path,
    ) -> None:
        """Record final artifact packaging with hash."""
        sha = _sha256(zip_path)
        self._counts["packages"] += 1
        self._packages.append({
            "skill": skill_name,
            "path": str(zip_path),
            "sha256": sha or "unknown",
        })
        self._write({
            "event": "package",
            "skill": skill_name,
            "zip_path": str(zip_path),
            "sha256": sha,
        })

    def log_message(self, event: str, **kwargs: Any) -> None:
        """Write an ad-hoc event record."""
        self._write({"event": event, **kwargs})

    def finalize(self) -> Path:
        """
        Write a session_summary.json and return its path.
        Safe to call multiple times (idempotent after first call).
        """
        summary = {
            "ts": _now_iso(),
            "log_file": str(self._log_path),
            "run_dir": str(self._run_dir),
            "counts": self._counts,
            "total_errors": len(self._errors),
            "unique_errors": list(dict.fromkeys(self._errors)),
            "packages": self._packages,
        }
        try:
            self._summary_path.write_text(
                json.dumps(summary, indent=2, default=str), encoding="utf-8"
            )
        except OSError as exc:
            logger.warning("EvidenceLogger.finalize: could not write summary: %s", exc)
        return self._summary_path

    @property
    def log_path(self) -> Path:
        return self._log_path

    @property
    def summary_path(self) -> Path:
        return self._summary_path

    @property
    def run_dir(self) -> Path:
        return self._run_dir
