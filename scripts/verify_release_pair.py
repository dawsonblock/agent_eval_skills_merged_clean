#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import zipfile


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LOCK = REPO_ROOT / "release_artifacts" / "release_lock.json"

FORBIDDEN_SUBSTRINGS = [
    "/node_modules/",
    "/.skillforge/",
    "/__pycache__/",
    ".DS_Store",
    "__MACOSX/",
]


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_lock(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def matches_locked_artifact(path: Path, locked_value: str) -> bool:
    locked_path = Path(locked_value)
    if path.name == locked_path.name:
        return True
    try:
        rel = path.resolve().relative_to(REPO_ROOT.resolve()).as_posix()
    except ValueError:
        return False
    return rel == locked_path.as_posix()


def zip_entries(path: Path) -> list[str]:
    with zipfile.ZipFile(path) as zf:
        return zf.namelist()


def has_forbidden_entries(entries: list[str]) -> list[str]:
    found: list[str] = []
    for entry in entries:
        normalized = f"/{entry}"
        for token in FORBIDDEN_SUBSTRINGS:
            if token in normalized or entry.startswith("/"):
                found.append(entry)
                break
            if "/Users/" in normalized or "/home/" in normalized:
                found.append(entry)
                break
    return found


def evidence_has_validation_summary(evidence_zip: Path) -> bool:
    names = set(zip_entries(evidence_zip))
    candidates = {
        "release_artifacts/validation_summary.json",
        "release_artifacts/validation_logs/validation_summary.json",
        ".validation_logs/validation_summary.json",
        "validation_summary.json",
    }
    return any(name in names for name in candidates)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Verify canonical release/evidence pair against release lock"
    )
    parser.add_argument("--release", type=Path, required=True)
    parser.add_argument("--evidence", type=Path, required=True)
    parser.add_argument("--lock", type=Path, default=DEFAULT_LOCK)
    args = parser.parse_args()

    lock = load_lock(args.lock)

    release_path = args.release
    evidence_path = args.evidence

    errors: list[str] = []

    if not release_path.exists():
        errors.append(f"release missing: {release_path}")
    if not evidence_path.exists():
        errors.append(f"evidence missing: {evidence_path}")
    if errors:
        for item in errors:
            print(f"FAIL: {item}")
        return 1

    if not matches_locked_artifact(release_path, lock["release_zip"]):
        errors.append("release filename mismatch against lock")
    if not matches_locked_artifact(evidence_path, lock["evidence_zip"]):
        errors.append("evidence filename mismatch against lock")

    release_sha = sha256_of(release_path)
    evidence_sha = sha256_of(evidence_path)

    if release_sha != lock["release_sha256"]:
        errors.append("release hash mismatch against lock")
    if evidence_sha != lock["evidence_sha256"]:
        errors.append("evidence hash mismatch against lock")

    if not evidence_has_validation_summary(evidence_path):
        errors.append("evidence missing validation_summary.json")

    release_forbidden = has_forbidden_entries(zip_entries(release_path))
    if release_forbidden:
        errors.append("release contains forbidden entries")

    evidence_forbidden = has_forbidden_entries(zip_entries(evidence_path))
    if evidence_forbidden:
        errors.append("evidence contains forbidden entries")

    if errors:
        print("FAIL: release and evidence pair verification failed")
        for item in errors:
            print(f"- {item}")
        return 1

    print("PASS: release and evidence pair verified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
