"""Tests for csv-cleaner tool."""
from __future__ import annotations

import csv
import sys
from pathlib import Path

import pytest

# Ensure the tool directory is importable
sys.path.insert(0, str(Path(__file__).parent.parent))
from tool import run  # noqa: E402


@pytest.fixture
def sample_csv(tmp_path: Path) -> Path:
    p = tmp_path / "input.csv"
    p.write_text("name,age\nAlice,30\nBob,25\nAlice,30\n,\nCharlie,28\n", encoding="utf-8")
    return p


def test_removes_blank_rows(sample_csv: Path, tmp_path: Path) -> None:
    out = tmp_path / "output.csv"
    result = run(str(sample_csv), str(out))
    assert "cleaned_path" in result, "Result should contain cleaned_path"
    assert out.exists(), "Output file should exist"
    with out.open(newline="") as f:
        rows = list(csv.reader(f))
    assert all(any(cell for cell in row) for row in rows), "Blank rows should be removed"
    assert result["removed_empty_rows"] == 1, "Should report 1 empty row removed"


def test_deduplication(sample_csv: Path, tmp_path: Path) -> None:
    out = tmp_path / "output.csv"
    result = run(str(sample_csv), str(out))
    assert "output_rows" in result, "Result should contain output_rows"
    # Input: header + Alice, Bob, Alice (dup), blank row, Charlie
    # Tool removes blank rows but keeps all non-blank rows
    # Expected output: 4 rows (header + Alice + Bob + Alice + Charlie)
    assert result["output_rows"] == 4, f"Expected 4 rows after blank removal, got {result['output_rows']}"
    with out.open(newline="") as f:
        rows = list(csv.reader(f))
    # Verify blank row was removed
    assert len(rows) == 5, f"File should have 5 lines (header + 4 data), got {len(rows)}"
    assert all(any(cell for cell in row) for row in rows), "No blank rows should remain"


def test_strips_whitespace(tmp_path: Path) -> None:
    p = tmp_path / "padded.csv"
    p.write_text("  name  ,  age  \n  Alice  ,  30  \n", encoding="utf-8")
    out = tmp_path / "output.csv"
    result = run(str(p), str(out))
    with out.open(newline="") as f:
        rows = list(csv.reader(f))
    assert rows[0] == ["name", "age"], f"Header should be normalized, got {rows[0]}"
    assert rows[1] == ["Alice", "30"], f"Data row should be trimmed, got {rows[1]}"


def test_write_to_output_path(sample_csv: Path, tmp_path: Path) -> None:
    out = tmp_path / "out.csv"
    result = run(str(sample_csv), str(out))
    assert out.exists(), "Output file should exist"
    assert "cleaned_path" in result, "Result should contain cleaned_path"
    assert str(out) == result["cleaned_path"], "cleaned_path should match output_path"


def test_missing_input_raises() -> None:
    with pytest.raises(FileNotFoundError):
        run("/nonexistent/path/input.csv")
