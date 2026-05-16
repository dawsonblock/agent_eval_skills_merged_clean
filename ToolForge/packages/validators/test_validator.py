"""
Test validator — runs pytest against a tool's test directory and reports results.
"""
from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from packages.core.safety_analyzer import analyze_safety
from packages.core.tool_spec import ToolSpec


@dataclass
class TestReport:
    passed: int = 0
    failed: int = 0
    errors: int = 0
    skipped: int = 0
    duration: float = 0.0
    failures: list[dict] = field(default_factory=list)

    @property
    def total(self) -> int:
        return self.passed + self.failed + self.errors

    @property
    def all_passed(self) -> bool:
        return self.failed == 0 and self.errors == 0


def run_tests(tool_dir: Path, timeout: int = 60) -> TestReport:
    """
    Run pytest in *tool_dir/tests/* and return a TestReport.
    Uses the current Python interpreter so the same venv is used.
    """
    tests_dir = tool_dir / "tests"
    if not tests_dir.exists():
        return TestReport()

    report = TestReport()
    json_output = tool_dir / ".pytest_report.json"

    cmd = [
        sys.executable, "-m", "pytest",
        str(tests_dir),
        "--tb=short",
        "-q",
        "--json-report",
        f"--json-report-file={json_output}",
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(tool_dir),
        )
    except subprocess.TimeoutExpired:
        report.errors = 1
        report.failures.append({"message": f"Tests timed out after {timeout}s"})
        return report
    except FileNotFoundError:
        # pytest not installed; fall back to counting with regex
        report.errors = 1
        report.failures.append({"message": "pytest not found in current environment"})
        return report

    # Check if pytest failed (returncode != 0)
    if result.returncode != 0:
        # Only treat as test failure if we couldn't parse the JSON report
        # (pytest itself returning nonzero means tests failed, which is still a failure)
        if not json_output.exists():
            report.errors = 1
            report.failures.append({
                "message": f"pytest exited with code {result.returncode}",
                "output": result.stdout + result.stderr,
            })

    # Parse JSON report if available
    if json_output.exists():
        try:
            data = json.loads(json_output.read_text())
            summary = data.get("summary", {})
            report.passed = summary.get("passed", 0)
            report.failed = summary.get("failed", 0)
            report.errors = summary.get("errors", 0)
            report.skipped = summary.get("skipped", 0)
            report.duration = data.get("duration", 0.0)
            for test in data.get("tests", []):
                if test.get("outcome") in ("failed", "error"):
                    report.failures.append({
                        "nodeid": test.get("nodeid", ""),
                        "message": test.get("call", {}).get("longrepr", ""),
                    })
        except (json.JSONDecodeError, KeyError):
            pass
        finally:
            json_output.unlink(missing_ok=True)
    else:
        # Fallback: parse stdout line "N passed, M failed"
        for line in result.stdout.splitlines():
            m_passed = __import__("re").search(r'(\d+) passed', line)
            m_failed = __import__("re").search(r'(\d+) failed', line)
            if m_passed:
                report.passed = int(m_passed.group(1))
            if m_failed:
                report.failed = int(m_failed.group(1))

def run_safety_checks(spec: ToolSpec, tool_dir: Path) -> TestReport:
    """
    Run static safety analysis against tool source code.
    Returns a TestReport with errors if unsafe patterns detected.
    """
    report = TestReport()
    
    try:
        safety_report = analyze_safety(spec, tool_dir)
        if safety_report.has_errors:
            report.errors = len([i for i in safety_report.issues if i.severity == "error"])
            for issue in safety_report.issues:
                if issue.severity == "error":
                    report.failures.append({
                        "code": issue.code,
                        "message": issue.message,
                        "file": issue.file,
                        "line": issue.line,
                    })
        else:
            # Safety checks passed
            report.passed = 1
    except Exception as e:
        report.errors = 1
        report.failures.append({"message": f"Safety analysis failed: {e}"})
    
    return report

    return report
