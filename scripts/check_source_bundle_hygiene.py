#!/usr/bin/env python3
# Fast forbidden-entries-only pre-check for source/release bundles.
#
# This script validates ZIP structural hygiene only: no path traversal,
# no absolute paths, no forbidden directories (node_modules, __pycache__, etc),
# and no release_artifacts/validation_logs entries.
#
# For the FULL release gate, use verify_source_bundle_hygiene.sh which additionally
# validates required layout paths (RELEASE_STATUS.json, RELEASE_MANIFEST.json,
# CLAIMS_MATRIX.md), release_classification fields, absolute local path scanning,
# and claims-matrix consistency.
#
# Relationship:
#   check_source_bundle_hygiene.py  → fast pre-check (forbidden entries only)
#   verify_source_bundle_hygiene.sh → canonical full gate (superset of this check)
from __future__ import annotations

import sys
import zipfile
from pathlib import Path, PurePosixPath

FORBIDDEN_PARTS = {
    ".skillforge",
    "node_modules",
    "__pycache__",
    ".pytest_cache",
}
FORBIDDEN_NAMES = {
    ".DS_Store",
}
FORBIDDEN_PATH_FRAGMENTS = {
    "release_artifacts/validation_logs",
}


def bad_entry(name: str) -> str | None:
    p = PurePosixPath(name)
    if name.startswith("/") or "\\" in name:
        return "absolute_or_windows_path"
    if ".." in p.parts:
        return "path_traversal"
    if any(part in FORBIDDEN_PARTS for part in p.parts):
        return "forbidden_directory"
    if p.name in FORBIDDEN_NAMES:
        return "forbidden_file"
    if any(fragment in name for fragment in FORBIDDEN_PATH_FRAGMENTS):
        return "forbidden_path"
    return None


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: check_source_bundle_hygiene.py <zip>")
        return 2

    path = Path(sys.argv[1])
    if not path.exists():
        print(f"FAIL: missing ZIP: {path}")
        return 1

    failures: list[tuple[str, str]] = []
    with zipfile.ZipFile(path) as zf:
        for info in zf.infolist():
            reason = bad_entry(info.filename)
            if reason:
                failures.append((info.filename, reason))

    if failures:
        print("FAIL: forbidden entries found")
        for name, reason in failures[:100]:
            print(f"{reason}: {name}")
        if len(failures) > 100:
            print(f"... {len(failures) - 100} more")
        return 1

    print("PASS: source bundle hygiene clean")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
