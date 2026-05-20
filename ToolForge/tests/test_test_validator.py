"""Tests for pytest execution validator behavior."""
from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from packages.validators import test_validator as test_validator_module
from packages.validators.test_validator import run_tests


def test_run_tests_reports_failures(tmp_path: Path) -> None:
    tests_dir = tmp_path / "tests"
    tests_dir.mkdir(parents=True)
    (tests_dir / "test_fail.py").write_text(
        "def test_fail():\n    assert False\n",
        encoding="utf-8",
    )

    report = run_tests(tmp_path)

    assert report is not None
    assert not report.all_passed
    assert report.failed > 0 or report.errors > 0


def test_run_tests_reports_passes(tmp_path: Path) -> None:
    tests_dir = tmp_path / "tests"
    tests_dir.mkdir(parents=True)
    (tests_dir / "test_ok.py").write_text(
        "def test_ok():\n    assert True\n",
        encoding="utf-8",
    )

    report = run_tests(tmp_path)

    assert report is not None
    assert report.all_passed
    assert report.passed == 1


def test_run_tests_cleans_invalid_json_report_by_default(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    tests_dir = tmp_path / "tests"
    tests_dir.mkdir(parents=True)
    (tests_dir / "test_ok.py").write_text("def test_ok():\n    assert True\n", encoding="utf-8")

    def _fake_run(cmd: list[str], cwd: Path, env: dict[str, str], timeout: float, grace_period: float = 0.5) -> subprocess.CompletedProcess[str]:
        del cwd, env, timeout, grace_period
        report_arg = next(a for a in cmd if a.startswith("--json-report-file="))
        report_path = Path(report_arg.split("=", 1)[1])
        report_path.write_text("{not-json", encoding="utf-8")
        return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="", stderr="")

    monkeypatch.setattr(test_validator_module, "run_with_process_tree_timeout", _fake_run)

    report = run_tests(tmp_path)

    assert report.errors >= 1
    assert not list(tmp_path.glob(".pytest_report_*.json"))


def test_run_tests_can_preserve_invalid_json_report_for_debugging(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    tests_dir = tmp_path / "tests"
    tests_dir.mkdir(parents=True)
    (tests_dir / "test_ok.py").write_text("def test_ok():\n    assert True\n", encoding="utf-8")

    def _fake_run(cmd: list[str], cwd: Path, env: dict[str, str], timeout: float, grace_period: float = 0.5) -> subprocess.CompletedProcess[str]:
        del cwd, env, timeout, grace_period
        report_arg = next(a for a in cmd if a.startswith("--json-report-file="))
        report_path = Path(report_arg.split("=", 1)[1])
        report_path.write_text("{not-json", encoding="utf-8")
        return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="", stderr="")

    monkeypatch.setattr(test_validator_module, "run_with_process_tree_timeout", _fake_run)
    monkeypatch.setenv("TOOLFORGE_PRESERVE_PYTEST_REPORT", "1")

    report = run_tests(tmp_path)

    assert report.errors >= 1
    reports = list(tmp_path.glob(".pytest_report_*.json"))
    assert len(reports) == 1


def test_run_tests_uses_pytest_timeout_when_available(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    tests_dir = tmp_path / "tests"
    tests_dir.mkdir(parents=True)
    (tests_dir / "test_ok.py").write_text("def test_ok():\n    assert True\n", encoding="utf-8")

    captured_cmds: list[list[str]] = []

    def _fake_run(cmd: list[str], cwd: Path, env: dict[str, str], timeout: float, grace_period: float = 0.5) -> subprocess.CompletedProcess[str]:
        del cwd, env, timeout, grace_period
        captured_cmds.append(cmd)
        report_arg = next(a for a in cmd if a.startswith("--json-report-file="))
        report_path = Path(report_arg.split("=", 1)[1])
        report_path.write_text(
            '{"summary": {"passed": 1, "failed": 0, "errors": 0, "skipped": 0}, "duration": 0.01, "tests": []}',
            encoding="utf-8",
        )
        return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="", stderr="")

    monkeypatch.setattr(test_validator_module, "run_with_process_tree_timeout", _fake_run)
    monkeypatch.setattr(test_validator_module, "has_pytest_timeout", lambda: True)

    report = run_tests(tmp_path)

    assert report.all_passed
    assert captured_cmds
    cmd = captured_cmds[0]
    assert "pytest_timeout" in cmd
    assert "--timeout=30" in cmd


def test_run_tests_skips_pytest_timeout_when_unavailable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    tests_dir = tmp_path / "tests"
    tests_dir.mkdir(parents=True)
    (tests_dir / "test_ok.py").write_text("def test_ok():\n    assert True\n", encoding="utf-8")

    captured_cmds: list[list[str]] = []

    def _fake_run(cmd: list[str], cwd: Path, env: dict[str, str], timeout: float, grace_period: float = 0.5) -> subprocess.CompletedProcess[str]:
        del cwd, env, timeout, grace_period
        captured_cmds.append(cmd)
        report_arg = next(a for a in cmd if a.startswith("--json-report-file="))
        report_path = Path(report_arg.split("=", 1)[1])
        report_path.write_text(
            '{"summary": {"passed": 1, "failed": 0, "errors": 0, "skipped": 0}, "duration": 0.01, "tests": []}',
            encoding="utf-8",
        )
        return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="", stderr="")

    monkeypatch.setattr(test_validator_module, "run_with_process_tree_timeout", _fake_run)
    monkeypatch.setattr(test_validator_module, "has_pytest_timeout", lambda: False)

    report = run_tests(tmp_path)

    assert report.all_passed
    assert captured_cmds
    cmd = captured_cmds[0]
    assert "pytest_timeout" not in cmd
    assert "--timeout=30" not in cmd
