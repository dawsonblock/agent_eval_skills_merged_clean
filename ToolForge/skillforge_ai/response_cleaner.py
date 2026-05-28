from __future__ import annotations

import re


def clean_response_text(value: str, *, max_lines: int = 40) -> str:
    """Normalize assistant text for cleaner, more readable chat output.

    - Trims leading/trailing whitespace
    - Collapses excessive blank lines
    - Strips trailing spaces per line
    - Caps overly verbose responses to a sane line count
    """

    text = (value or "").replace("\r\n", "\n").strip()
    if not text:
        return ""

    lines = [line.rstrip() for line in text.split("\n")]
    normalized = "\n".join(lines)
    normalized = re.sub(r"\n{3,}", "\n\n", normalized)

    clipped_lines = normalized.split("\n")
    if len(clipped_lines) > max_lines:
        clipped_lines = clipped_lines[:max_lines]
        clipped_lines.append("... (truncated)")
    return "\n".join(clipped_lines).strip()
