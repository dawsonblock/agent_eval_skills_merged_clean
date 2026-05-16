"""
csv-cleaner — removes blank rows, strips whitespace, deduplicates a CSV file.

Inputs (via TOOLFORGE_INPUTS env var, JSON dict):
  input_path  (str, required) — path to input CSV
  output_path (str, optional) — path to write cleaned CSV; prints to stdout if omitted
"""
from __future__ import annotations

import csv
import io
import json
import os
import sys
from pathlib import Path


def clean_csv(input_path: str, output_path: str | None = None) -> str:
    src = Path(input_path)
    if not src.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    text = src.read_text(encoding="utf-8-sig")  # handle BOM
    reader = csv.reader(io.StringIO(text))

    rows: list[list[str]] = []
    seen: set[tuple[str, ...]] = set()

    for raw_row in reader:
        stripped = [cell.strip() for cell in raw_row]
        # Skip fully blank rows
        if not any(stripped):
            continue
        key = tuple(stripped)
        if key in seen:
            continue
        seen.add(key)
        rows.append(stripped)

    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerows(rows)
    result = out.getvalue()

    if output_path:
        Path(output_path).write_text(result, encoding="utf-8")
        return f"Cleaned CSV written to {output_path} ({len(rows)} rows)"
    return result


def main() -> None:
    raw = os.environ.get("TOOLFORGE_INPUTS", "{}")
    try:
        inputs = json.loads(raw)
    except json.JSONDecodeError as e:
        print(f"Error parsing inputs: {e}", file=sys.stderr)
        sys.exit(1)

    input_path = inputs.get("input_path")
    if not input_path:
        print("Error: 'input_path' is required.", file=sys.stderr)
        sys.exit(1)

    output_path = inputs.get("output_path")

    try:
        result = clean_csv(input_path, output_path)
        print(result, end="")
    except Exception as e:  # noqa: BLE001
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
