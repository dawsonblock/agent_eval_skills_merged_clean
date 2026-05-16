"""Tests for csv-cleaner tool."""
from __future__ import annotations

import csv
import io
import sys
from pathlib import Path

import pytest

# Ensure the tool directory is importable
sys.path.insert(0, str(Path(__file__).parent.parent))
from tool import clean_csv  # noqa: E402


@pytest.fixture
def sample_csv(tmp_path: Path) -> Path:
    p = tmp_path / "input.csv"
    p.write_text("name,age\nAlice,30\nBob,25\nAlice,30\n,\nCharlie,28\n", encoding="utf-8")
    return p


def test_removes_blank_rows(sample_csv: Path) -> None:
    result = clean_csv(str(sample_csv))
    rows = list(csv.reader(io.StringIO(result)))
    assert all(any(cell for cell in row) for row in rows), "Blank rows should be removed"


def test_deduplication(sample_csv: Path) -> None:
    result = clean_csv(str(sample_csv))
    rows = list(csv.reader(io.StringIO(result)))
    assert len(rows) == 4, f"Expected 4 unique rows (header + 3 data), got {len(rows)}"


def test_strips_whitespace(tmp_path: Path) -> None:
    p = tmp_path / "padded.csv"
    p.write_text("  name  ,  age  \n  Alice  ,  30  \n", encoding="utf-8")
    result = clean_csv(str(p))
    rows = list(csv.reader(io.StringIO(result)))
    assert rows[0] == ["name", "age"]
    assert rows[1] == ["Alice", "30"]


def test_write_to_output_path(sample_csv: Path, tmp_path: Path) -> None:
    out = tmp_path / "out.csv"
    msg = clean_csv(str(sample_csv), str(out))
    assert out.exists()
    assert "Cleaned CSV written to" in msg


def test_missing_input_raises() -> None:
    with pytest.raises(FileNotFoundError):
        clean_csv("/nonexistent/path/input.csv")
