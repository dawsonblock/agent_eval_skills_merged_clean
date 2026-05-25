"""Website table scraper for SkillForge MVP packaging and smoke runs."""
from __future__ import annotations

import json
import os
import re
import sys
from html.parser import HTMLParser
from pathlib import Path


class _TableParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.tables: list[list[list[str]]] = []
        self._current_table: list[list[str]] | None = None
        self._current_row: list[str] | None = None
        self._collect_cell = False
        self._cell_fragments: list[str] = []

    def handle_starttag(
        self,
        tag: str,
        attrs: list[tuple[str, str | None]],
    ) -> None:
        del attrs
        lowered = tag.lower()
        if lowered == "table":
            self._current_table = []
        elif lowered == "tr" and self._current_table is not None:
            self._current_row = []
        elif lowered in {"th", "td"} and self._current_row is not None:
            self._collect_cell = True
            self._cell_fragments = []

    def handle_data(self, data: str) -> None:
        if self._collect_cell:
            self._cell_fragments.append(data)

    def handle_endtag(self, tag: str) -> None:
        lowered = tag.lower()
        if lowered in {"th", "td"} and self._current_row is not None:
            cell = re.sub(r"\s+", " ", "".join(self._cell_fragments)).strip()
            self._current_row.append(cell)
            self._collect_cell = False
            self._cell_fragments = []
        elif (
            lowered == "tr"
            and self._current_table is not None
            and self._current_row is not None
        ):
            if self._current_row:
                self._current_table.append(self._current_row)
            self._current_row = None
        elif lowered == "table" and self._current_table is not None:
            if self._current_table:
                self.tables.append(self._current_table)
            self._current_table = None


def _parse_tables(html_text: str) -> list[dict[str, list[dict[str, str]]]]:
    parser = _TableParser()
    parser.feed(html_text)

    output: list[dict[str, list[dict[str, str]]]] = []
    for table in parser.tables:
        if not table:
            continue
        header = table[0]
        rows = table[1:]
        mapped_rows: list[dict[str, str]] = []
        for row in rows:
            record: dict[str, str] = {}
            for idx, key in enumerate(header):
                value = row[idx] if idx < len(row) else ""
                record[key or f"col_{idx + 1}"] = value
            mapped_rows.append(record)
        output.append({"rows": mapped_rows})
    return output


def run(
    input_path: str,
    output_path: str | None = None,
) -> dict[str, str | int]:
    source = Path(input_path)
    if source.suffix.lower() not in {".html", ".htm"}:
        raise ValueError("input_path must point to a .html or .htm file")
    if not source.exists():
        raise FileNotFoundError(f"Input file not found: {source}")

    output = (
        Path(output_path)
        if output_path
        else source.with_suffix(".tables.json")
    )
    output.parent.mkdir(parents=True, exist_ok=True)

    tables = _parse_tables(source.read_text(encoding="utf-8"))
    payload = {"tables": tables}
    output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    return {
        "json_path": str(output),
        "table_count": len(tables),
    }


if __name__ == "__main__":
    raw = os.environ.get("TOOLFORGE_INPUTS")
    if not raw:
        print(
            json.dumps({"error": "TOOLFORGE_INPUTS is required"}),
            file=sys.stderr,
        )
        raise SystemExit(2)
    try:
        payload = json.loads(raw)
        print(json.dumps(run(**payload), indent=2, sort_keys=True))
    except Exception as exc:  # noqa: BLE001
        print(
            json.dumps({"error": str(exc), "type": exc.__class__.__name__}),
            file=sys.stderr,
        )
        raise SystemExit(1)
