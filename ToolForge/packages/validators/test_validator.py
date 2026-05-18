"""
Test validator — runs pytest against a tool's test directory and reports results.
"""
from __future__ import annotations

import json
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

from packages.core.process_timeout import run_with_process_tree_timeout
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
        sys.executable,
        "-m",
        "pytest",
        "-p",
        "pytest_jsonreport.plugin",
        "-p",
        "pytest_cov.plugin",
        str(tests_dir),
        "-o",
        "addopts=",
        "--no-cov",
        "--tb=short",
        "-q",
        "--json-report",
        f"--json-report-file={json_output}",
    ]

    fallback_cmd = [
        sys.executable,
        "-m",
        "pytest",
        "-p",
        "pytest_cov.plugin",
        str(tests_dir),
        "-o",
        "addopts=",
        "--no-cov",
        "--tb=short",
        "-q",
    ]

    nested_env = os.environ.copy()
    nested_env.pop("PYTEST_CURRENT_TEST", None)
    nested_env.pop("PYTEST_ADDOPTS", None)
    nested_env.pop("PYTEST_PLUGINS", None)
    nested_env["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
    nested_env["PYTHONDONTWRITEBYTECODE"] = "1"
    nested_env["TOOLFORGE_NESTED_PYTEST"] = "1"

    try:
        result = run_with_process_tree_timeout(
            cmd, tool_dir, nested_env, timeout, grace_period=0.5
        )
    except AssertionError as exc:
        # Timeout occurred - consolidated helper already killed process
        report.errors = 1
        report.failures.append({"message": str(exc)})
        return report
    except FileNotFoundError:
        # pytest not installed; fall back to counting with regex
        report.errors = 1
        report.failures.append({"message": "pytest not found in current environment"})
        return report

    combined_output = (result.stdout or "") + "\n" + (result.stderr or "")
    # Fall back if pytest_jsonreport plugin is not available or --json-report not recognized
    if result.returncode != 0 and (
        "unrecognized arguments: --json-report" in combined_output
        or "unknown option" in combined_output
        or "error: unrecognized arguments" in combined_output
    ):
        try:
            result = run_with_process_tree_timeout(
                fallback_cmd, tool_dir, nested_env, timeout, grace_period=0.5
            )
        except AssertionError as exc:
            # Timeout occurred - consolidated helper already killed process
            report.errors = 1
            report.failures.append({"message": str(exc)})
            return report

    had_json_report = json_output.exists()
    parsed_json = False
    parse_error = ""

    # Parse JSON report if available
    if had_json_report:
        try:
            data = json.loads(json_output.read_text())
            summary = data.get("summary", {})
            report.passed = summary.get("passed", 0)
            report.failed = summary.get("failed", 0)
            report.errors = summary.get("errors", 0)
            report.skipped = summary.get("skipped", 0)
            report.duration = data.get("duration", 0.0)
            parsed_json = True
            for test in data.get("tests", []):
                if test.get("outcome") in ("failed", "error"):
                    report.failures.append({
                        "nodeid": test.get("nodeid", ""),
                        "message": test.get("call", {}).get("longrepr", ""),
                    })
        except (json.JSONDecodeError, KeyError) as exc:
            parse_error = str(exc)
        finally:
            json_output.unlink(missing_ok=True)
    else:
        # Fallback: parse stdout line "N passed, M failed"
        for line in (result.stdout + "\n" + result.stderr).splitlines():
            m_passed = re.search(r"(\d+) passed", line)
            m_failed = re.search(r"(\d+) failed", line)
            m_error = re.search(r"(\d+) error", line)
            if m_passed:
                report.passed = int(m_passed.group(1))
            if m_failed:
                report.failed = int(m_failed.group(1))
            if m_error:
                report.errors = int(m_error.group(1))

    # Pytest returning nonzero must fail validation, even with parsed JSON.
    if result.returncode != 0 and report.failed == 0 and report.errors == 0:
        report.errors = 1

    if result.returncode != 0:
        report.failures.append(
            {
                "message": f"pytest exited with code {result.returncode}",
                "stdout": result.stdout[-2000:],
                "stderr": result.stderr[-2000:],
            }
        )

    if had_json_report and not parsed_json:
        report.errors = max(report.errors, 1)
        report.failures.append(
            {
                "message": "pytest JSON report could not be parsed",
                "error": parse_error,
            }
        )

    # If tests directory exists but nothing collected, fail for generated tools.
    if report.total == 0:
        report.errors = max(report.errors, 1)
        report.failures.append({"message": "No tests were collected"})

    return report

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
    except Exception as exc:
        report.errors = 1
        report.failures.append({"message": f"Safety analysis failed: {exc}"})
    
    return report
