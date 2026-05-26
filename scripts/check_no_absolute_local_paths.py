#!/usr/bin/env python3
from __future__ import annotations

import pathlib
import re
import sys
from argparse import ArgumentParser

ROOT = pathlib.Path(__file__).resolve().parents[1]

BAD_PATTERNS = [
    re.compile(r"/Users/[^/\s]+/"),
    re.compile(r"/home/[^/\s]+/"),
    re.compile(r"C:\\\\Users\\\\", re.IGNORECASE),
    re.compile(r"/mnt/data/"),
]

SCAN_EXTS = {".json", ".md", ".txt", ".yaml", ".yml"}

IGNORE_PARTS = {
    ".git",
    "node_modules",
    "__pycache__",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".skillforge",
    ".venv",
    "htmlcov",
    "withdrawn",
}

RELEASE_TRUTH_FILES = {
    "README.md",
    "CLAIMS_MATRIX.md",
    "RELEASE_STATUS.json",
    "RELEASE_MANIFEST.json",
    "RELEASE_EVIDENCE_APPENDIX.md",
    "release_artifacts/RELEASE_EVIDENCE_APPENDIX.md",
}


def should_scan(rel_s: str, strict: bool) -> bool:
    if rel_s in RELEASE_TRUTH_FILES:
        return True
    if rel_s.startswith("scripts/"):
        return True

    if strict:
        return rel_s.startswith("release_artifacts/") or rel_s.startswith(".validation_logs/")

    if rel_s.startswith("release_artifacts/current/"):
        return True
    if rel_s.startswith("release_artifacts/SKILLFORGE_") and rel_s.endswith(".json"):
        return True
    if rel_s.startswith("release_artifacts/skillforge_ai_") and rel_s.endswith(".json"):
        return True

    return False

parser = ArgumentParser(description="Check release-facing artifacts for absolute local path leaks")
parser.add_argument("--strict", action="store_true", help="Include release_artifacts and .validation_logs in the scan")
args = parser.parse_args()

errors: list[str] = []

for path in ROOT.rglob("*"):
    if not path.is_file():
        continue
    if path.suffix.lower() not in SCAN_EXTS:
        continue
    if any(part in IGNORE_PARTS for part in path.parts):
        continue

    rel = path.relative_to(ROOT)
    rel_s = rel.as_posix()
    if not should_scan(rel_s, strict=args.strict):
        continue

    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        continue

    for pattern in BAD_PATTERNS:
        if pattern.search(text):
            errors.append(str(path.relative_to(ROOT)))
            break

if errors:
    print("Absolute local paths found:")
    for item in sorted(errors):
        print(f" - {item}")
    sys.exit(1)

print("No absolute local path leaks found.")
