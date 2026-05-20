"""
Integration tests for test_validator that actually run nested pytest subprocesses.
"""
import pytest
from pathlib import Path
from packages.validators.test_validator import run_tests

pytestmark = pytest.mark.integration

def test_run_tests_reports_failures_integration(tmp_path: Path) -> None:
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

def test_run_tests_reports_passes_integration(tmp_path: Path) -> None:
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
