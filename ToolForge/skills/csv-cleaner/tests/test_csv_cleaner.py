"""Auto-generated tests for csv-cleaner."""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from tool import run


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_clean_csv_file(tmp_path: Path) -> None:
    input_csv = tmp_path / "input.csv"
    output_csv = tmp_path / "cleaned.csv"
    _write(
        input_csv,
        " Name , Name , City\nAlice , Alice A , Saskatoon\n\n, ,\n Bob , Bob B , Regina\n",
    )

    result = run(input_path=str(input_csv), output_path=str(output_csv))

    assert output_csv.exists()
    assert result["cleaned_path"] == str(output_csv)
    assert result["removed_empty_rows"] == 2
    assert result["output_rows"] == 2
    assert result["headers"] == ["name", "name_2", "city"]

    with output_csv.open("r", encoding="utf-8", newline="") as fh:
        rows = list(csv.reader(fh))
    assert rows[0] == ["name", "name_2", "city"]


def test_reject_non_csv(tmp_path: Path) -> None:
    bad = tmp_path / "input.txt"
    _write(bad, "hello")
    try:
        run(input_path=str(bad))
    except ValueError as exc:
        assert ".csv" in str(exc)
    else:
        raise AssertionError("Expected ValueError for non-csv input")


def test_empty_csv(tmp_path: Path) -> None:
    empty = tmp_path / "empty.csv"
    output_csv = tmp_path / "empty_out.csv"
    _write(empty, "")
    result = run(input_path=str(empty), output_path=str(output_csv))
    assert output_csv.exists()
    assert result["output_rows"] == 0


def test_duplicate_headers(tmp_path: Path) -> None:
    input_csv = tmp_path / "dup.csv"
    output_csv = tmp_path / "dup_out.csv"
    _write(input_csv, "Name,Name,Name\nAlice,A,A2\n")
    result = run(input_path=str(input_csv), output_path=str(output_csv))
    assert result["headers"] == ["name", "name_2", "name_3"]


def test_write_json_output(tmp_path: Path) -> None:
    input_csv = tmp_path / "input.csv"
    output_json = tmp_path / "cleaned.json"
    _write(input_csv, "Name, Age\n Alice , 30 \n Bob , 41 \n")

    result = run(input_path=str(input_csv), output_path=str(output_json))

    assert output_json.exists()
    assert result["cleaned_path"] == str(output_json)

    payload = json.loads(output_json.read_text(encoding="utf-8"))
    assert payload["cleaned_path"] == str(output_json)
    assert payload["headers"] == ["name", "age"]
    assert payload["rows"] == [
        {"name": "Alice", "age": "30"},
        {"name": "Bob", "age": "41"},
    ]
