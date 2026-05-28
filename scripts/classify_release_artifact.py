#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LOCK = REPO_ROOT / "release_artifacts" / "release_lock.json"


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def emit(path: Path | None, payload: dict) -> None:
    rendered = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    if path is None:
        print(rendered, end="")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(rendered, encoding="utf-8")


def matches_locked_artifact(path: Path, locked_value: str) -> bool:
    locked_path = Path(locked_value)
    if path.name == locked_path.name:
        return True
    try:
        rel = path.resolve().relative_to(REPO_ROOT.resolve()).as_posix()
    except ValueError:
        return False
    return rel == locked_path.as_posix()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Classify release archive against canonical lock metadata"
    )
    parser.add_argument("archive", type=Path, help="Archive path to classify")
    parser.add_argument("--json-out", type=Path)
    parser.add_argument("--lock", type=Path, default=DEFAULT_LOCK)
    parser.add_argument("--evidence", type=Path)
    args = parser.parse_args()

    if not args.archive.exists():
        missing_payload = {
            "status": "fail",
            "verdict": "missing_artifact",
            "canonical": False,
            "path": str(args.archive),
            "reasons": ["artifact path does not exist"],
        }
        emit(args.json_out, missing_payload)
        return 1

    lock = json.loads(args.lock.read_text(encoding="utf-8"))
    archive_sha = sha256_of(args.archive)

    reasons: list[str] = []
    canonical = False
    verdict = "unbound_wrapper_source_bundle"

    release_path = REPO_ROOT / "release_artifacts" / lock["release_zip"]
    evidence_path = REPO_ROOT / "release_artifacts" / lock["evidence_zip"]

    if not matches_locked_artifact(args.archive, lock["release_zip"]):
        reasons.append("release filename mismatch")
    if archive_sha != lock["release_sha256"]:
        reasons.append("release hash mismatch")

    if args.evidence is None:
        reasons.append("no evidence pair provided")
    elif not args.evidence.exists():
        reasons.append("evidence artifact path does not exist")
    else:
        evidence_sha = sha256_of(args.evidence)
        if not matches_locked_artifact(args.evidence, lock["evidence_zip"]):
            reasons.append("evidence filename mismatch")
        if evidence_sha != lock["evidence_sha256"]:
            reasons.append("evidence hash mismatch")

    if args.archive.resolve() != release_path.resolve() and archive_sha != lock["release_sha256"]:
        verdict = "unbound_wrapper_source_bundle"
        payload = {
            "status": "pass",
            "verdict": verdict,
            "canonical": False,
            "archive": {
                "path": str(args.archive),
                "name": args.archive.name,
                "sha256": archive_sha,
            },
            "reasons": reasons,
        }
        emit(args.json_out, payload)
        return 0

    if not reasons:
        verdict = "canonical_smoke_release"
        canonical = True

    payload: dict[str, object] = {
        "status": "pass",
        "verdict": verdict,
        "canonical": canonical,
        "archive": {
            "path": str(args.archive),
            "name": args.archive.name,
            "sha256": archive_sha,
        },
        "reasons": reasons,
    }
    emit(args.json_out, payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
