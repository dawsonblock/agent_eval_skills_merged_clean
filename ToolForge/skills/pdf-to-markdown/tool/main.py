"""PDF to Markdown converter for SkillForge MVP packaging and smoke runs."""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path


def _extract_text(pdf_bytes: bytes) -> str:
    # Pull printable runs from PDF-like bytes without external dependencies.
    chunks = re.findall(rb"[ -~]{4,}", pdf_bytes)
    text = "\n".join(
        chunk.decode("latin-1", errors="ignore")
        for chunk in chunks
    )
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _to_markdown(text: str) -> str:
    if not text:
        return "# Extracted Document\n\n"
    return "# Extracted Document\n\n" + text + "\n"


def run(
    input_path: str,
    output_path: str | None = None,
) -> dict[str, str | int]:
    source = Path(input_path)
    if source.suffix.lower() != ".pdf":
        raise ValueError("input_path must point to a .pdf file")
    if not source.exists():
        raise FileNotFoundError(f"Input file not found: {source}")

    output = Path(output_path) if output_path else source.with_suffix(".md")
    output.parent.mkdir(parents=True, exist_ok=True)

    text = _extract_text(source.read_bytes())
    markdown = _to_markdown(text)
    output.write_text(markdown, encoding="utf-8")

    return {
        "markdown_path": str(output),
        "characters": len(markdown),
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
