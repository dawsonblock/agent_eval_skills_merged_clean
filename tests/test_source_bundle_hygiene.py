from __future__ import annotations

import subprocess
import sys
import zipfile
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]


def _write_zip(path: Path, names: list[str]) -> None:
    with zipfile.ZipFile(path, "w") as zf:
        for name in names:
            zf.writestr(name, "test")


def _run_hygiene_check(path: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "scripts/check_source_bundle_hygiene.py", str(path)],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


@pytest.mark.parametrize(
    "dirty_entry",
    [
        "__MACOSX/._README.md",
        "folder/._file",
        ".validation_logs/validation_summary.json",
        "release_artifacts/validation_logs/root.txt",
        "node_modules/package/index.js",
    ],
)
def test_source_bundle_hygiene_rejects_forbidden_entries(
    tmp_path: Path, dirty_entry: str
) -> None:
    archive = tmp_path / "dirty.zip"
    _write_zip(archive, ["README.md", dirty_entry])

    result = _run_hygiene_check(archive)

    assert result.returncode == 1
    assert "FAIL: forbidden entries found" in result.stdout
    assert dirty_entry in result.stdout


def test_source_bundle_hygiene_accepts_clean_archive(tmp_path: Path) -> None:
    archive = tmp_path / "clean.zip"
    _write_zip(archive, ["README.md", "ToolForge/README.md"])

    result = _run_hygiene_check(archive)

    assert result.returncode == 0
    assert "PASS: source bundle hygiene clean" in result.stdout
