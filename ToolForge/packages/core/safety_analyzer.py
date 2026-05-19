"""
Safety analyzer — static analysis of a generated tool directory.

Checks:
  - Denied import patterns from security_policy.yaml
  - Shell command patterns in source files
  - Path traversal patterns
  - Hardcoded secrets / tokens
  - Capability / sandbox level consistency
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from packages.core.tool_spec import ToolSpec


@dataclass
class SafetyIssue:
    severity: str  # "error" | "warning" | "info"
    code: str
    message: str
    file: str | None = None
    line: int | None = None


@dataclass
class SafetyReport:
    tool_slug: str
    issues: list[SafetyIssue] = field(default_factory=list)

    @property
    def has_errors(self) -> bool:
        return any(i.severity == "error" for i in self.issues)

    @property
    def issue_count(self) -> int:
        return len(self.issues)

    @property
    def has_warnings(self) -> bool:
        return any(i.severity == "warning" for i in self.issues)

    def summary(self) -> str:
        errors = sum(1 for i in self.issues if i.severity == "error")
        warnings = sum(1 for i in self.issues if i.severity == "warning")
        return f"{errors} error(s), {warnings} warning(s)"


# Patterns that are always suspicious in generated code
_SECRET_PATTERNS = [
    (re.compile(r'(?i)(password|passwd|secret|api_key|token)\s*=\s*["\'][^"\']{6,}["\']'), "HARDCODED_SECRET"),
    (re.compile(r'sk-[A-Za-z0-9]{20,}'), "OPENAI_KEY_LITERAL"),
    (re.compile(r'(?i)aws_secret_access_key\s*=\s*["\'][^"\']+["\']'), "AWS_SECRET_LITERAL"),
]

# Imports denied unless requires_shell=True
_DENIED_IMPORTS_SHELL = [
    "subprocess", "os.system", "popen", "pty", "ctypes", "cffi",
]

# Imports denied unless requires_network=True (or requires_shell=True)
_DENIED_IMPORTS_NETWORK = [
    "socket", "asyncio.create_subprocess",
]

_TRAVERSAL_PATTERN = re.compile(r'\.\.[/\\]')

_SHELL_EXEC_PATTERN = re.compile(r'(subprocess\.(?:run|call|Popen|check_output)|os\.system|eval\(|exec\()')


def analyze_safety(spec: ToolSpec, tool_dir: Path) -> SafetyReport:
    """
    Run static safety checks against all Python source files in *tool_dir*.
    """
    report = SafetyReport(tool_slug=spec.slug)

    # 1. Capability / sandbox level check
    if spec.security.requires_shell and spec.sandbox_level < 2:
        report.issues.append(SafetyIssue(
            severity="error",
            code="SANDBOX_TOO_LOW",
            message=f"requires_shell=True but sandbox_level={spec.sandbox_level}; minimum is 2",
        ))

    if spec.security.requires_network and spec.sandbox_level < 1:
        report.issues.append(SafetyIssue(
            severity="error",
            code="SANDBOX_TOO_LOW",
            message=f"requires_network=True but sandbox_level={spec.sandbox_level}; minimum is 1",
        ))

    # 2. Static file analysis
    py_files = list(tool_dir.rglob("*.py"))
    for py_file in py_files:
        rel = str(py_file.relative_to(tool_dir))
        try:
            lines = py_file.read_text(encoding="utf-8").splitlines()
        except OSError:
            report.issues.append(SafetyIssue(
                severity="warning",
                code="UNREADABLE_FILE",
                message=f"Could not read {rel}: skipped from safety analysis",
                file=rel,
            ))
            continue

        for lineno, line in enumerate(lines, start=1):
            # Secret patterns
            for pattern, code in _SECRET_PATTERNS:
                if pattern.search(line):
                    report.issues.append(SafetyIssue(
                        severity="error", code=code,
                        message=f"Possible hardcoded secret: {line.strip()[:80]}",
                        file=rel, line=lineno,
                    ))

            # Path traversal
            if _TRAVERSAL_PATTERN.search(line):
                report.issues.append(SafetyIssue(
                    severity="warning", code="PATH_TRAVERSAL",
                    message=f"Possible path traversal: {line.strip()[:80]}",
                    file=rel, line=lineno,
                ))

            # Shell execution
            if _SHELL_EXEC_PATTERN.search(line) and not spec.security.requires_shell:
                report.issues.append(SafetyIssue(
                    severity="error", code="UNEXPECTED_SHELL",
                    message=(
                        f"Shell/exec call found but requires_shell=False: {line.strip()[:80]}"
                    ),
                    file=rel, line=lineno,
                ))

            # Denied imports — shell-specific
            for denied in _DENIED_IMPORTS_SHELL:
                if re.search(rf'\b{re.escape(denied)}\b', line) and not spec.security.requires_shell:
                    report.issues.append(SafetyIssue(
                        severity="error", code="DENIED_IMPORT",
                        message=f"Suspicious import/usage of {denied!r} in {rel}:{lineno}",
                        file=rel, line=lineno,
                    ))
                    break  # one warning per line
            else:
                # Denied imports — network-specific (allowed when requires_network=True)
                for denied in _DENIED_IMPORTS_NETWORK:
                    if (
                        re.search(rf'\b{re.escape(denied)}\b', line)
                        and not spec.security.requires_network
                        and not spec.security.requires_shell
                    ):
                        report.issues.append(SafetyIssue(
                            severity="error", code="DENIED_IMPORT",
                            message=f"Suspicious import/usage of {denied!r} in {rel}:{lineno}",
                            file=rel, line=lineno,
                        ))
                        break  # one warning per line

    return report
