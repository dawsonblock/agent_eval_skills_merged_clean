"""
Local PDF to Markdown converter (no OCR, no network).

This implementation extracts literal text operands from common PDF text-show
operators in uncompressed content streams: Tj and TJ arrays.
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path


STRING_RE = re.compile(rb"\((?P<text>(?:\\.|[^\\\)])*)\)")
Tj_RE = re.compile(rb"\((?:\\.|[^\\\)])*\)\s*Tj")
TJ_RE = re.compile(rb"\[(?P<items>[^\]]+)\]\s*TJ")


def _decode_pdf_literal(raw: bytes) -> str:
    # Handles escaped parentheses and common escaped characters.
    value = raw
    value = value.replace(rb"\\(", b"(").replace(rb"\\)", b")")
    value = value.replace(rb"\\n", b"\n").replace(rb"\\r", b"\n")
    value = value.replace(rb"\\t", b"\t").replace(rb"\\\\", b"\\")
    return value.decode("latin-1", errors="ignore")


def extract_text(pdf_bytes: bytes) -> list[str]:
    lines: list[str] = []

    for match in Tj_RE.finditer(pdf_bytes):
        segment = match.group(0)
        text_match = STRING_RE.search(segment)
        if not text_match:
            continue
        text = _decode_pdf_literal(text_match.group("text")).strip()
        if text:
            lines.append(text)

    for match in TJ_RE.finditer(pdf_bytes):
        items = match.group("items")
        parts: list[str] = []
        for text_match in STRING_RE.finditer(items):
            part = _decode_pdf_literal(text_match.group("text"))
            if part:
                parts.append(part)
        joined = "".join(parts).strip()
        if joined:
            lines.append(joined)

    return lines


def run(input_path: str, output_path: str | None = None) -> dict:
    input_file = Path(input_path)
    if not input_file.exists():
        raise FileNotFoundError(f"Input file not found: {input_file}")
    if input_file.suffix.lower() != ".pdf":
        raise ValueError("input_path must point to a .pdf file")

    markdown_file = Path(output_path) if output_path else Path("outputs") / "document.md"
    markdown_file.parent.mkdir(parents=True, exist_ok=True)

    lines = extract_text(input_file.read_bytes())
    if lines:
        markdown = "\n\n".join(f"- {line}" for line in lines)
    else:
        markdown = ""

    markdown_file.write_text(markdown + ("\n" if markdown else ""), encoding="utf-8")

    return {
        "input_path": str(input_file),
        "output_path": str(markdown_file),
        "lines_extracted": len(lines),
    }


def main() -> int:
    raw = os.environ.get("TOOLFORGE_INPUTS")
    if not raw:
        print(json.dumps({"error": "TOOLFORGE_INPUTS is required"}), file=sys.stderr)
        return 2

    try:
        inputs = json.loads(raw)
        result = run(**inputs)
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0
    except Exception as exc:  # noqa: BLE001
        print(
            json.dumps({"error": str(exc), "type": exc.__class__.__name__}),
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
