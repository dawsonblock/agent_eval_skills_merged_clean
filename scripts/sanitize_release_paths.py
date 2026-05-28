#!/usr/bin/env python3
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TARGET_DIRS = [ROOT / ".validation_logs", ROOT / "release_artifacts"]
TEXT_SUFFIXES = {".txt", ".log", ".json"}

ABSOLUTE_PATH_PATTERNS = [
    re.compile(r"/Users/[^/\s]+/[^\s\"']*"),
    re.compile(r"/home/[^/\s]+/[^\s\"']*"),
    re.compile(r"/mnt/data/[^\s\"']*"),
    re.compile(r"[A-Za-z]:\\\\Users\\\\[^\\\s\"']+\\\\[^\s\"']*"),
]


def _sanitize_string(value: str) -> str:
    root_str = str(ROOT)
    if root_str in value:
        value = value.replace(root_str, "${REPO_ROOT}")

    for pattern in ABSOLUTE_PATH_PATTERNS:
        value = pattern.sub("<LOCAL_PATH>", value)

    return value


def _sanitize_json(obj):
    if isinstance(obj, dict):
        return {key: _sanitize_json(val) for key, val in obj.items()}
    if isinstance(obj, list):
        return [_sanitize_json(item) for item in obj]
    if isinstance(obj, str):
        return _sanitize_string(obj)
    return obj


def _iter_json_files(base_dir: Path):
    if not base_dir.exists():
        return
    for path in sorted(base_dir.rglob("*.json")):
        if not path.is_file():
            continue
        if any(part in {"node_modules", "__pycache__", "withdrawn"} for part in path.parts):
            continue
        yield path


def _iter_text_files(base_dir: Path):
    if not base_dir.exists():
        return
    for path in sorted(base_dir.rglob("*")):
        if not path.is_file():
            continue
        if path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        if any(part in {"node_modules", "__pycache__", "withdrawn"} for part in path.parts):
            continue
        yield path


def main() -> int:
    changed = 0
    scanned_json = 0
    scanned_text = 0

    for base_dir in TARGET_DIRS:
        for json_path in _iter_json_files(base_dir):
            scanned_json += 1
            try:
                data = json.loads(json_path.read_text(encoding="utf-8"))
            except Exception:
                continue

            sanitized = _sanitize_json(data)
            if sanitized == data:
                continue

            json_path.write_text(
                json.dumps(sanitized, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            changed += 1

        for text_path in _iter_text_files(base_dir):
            scanned_text += 1
            raw = text_path.read_text(encoding="utf-8", errors="replace")
            sanitized = _sanitize_string(raw)
            if sanitized == raw:
                continue
            text_path.write_text(sanitized, encoding="utf-8")
            changed += 1

    print(
        f"Scanned {scanned_json} JSON and {scanned_text} text files; "
        f"sanitized {changed} file(s)."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
