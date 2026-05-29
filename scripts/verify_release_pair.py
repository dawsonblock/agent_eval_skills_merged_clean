#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from subprocess import run
import zipfile


ROOT = Path(__file__).resolve().parents[1]
LOCK = ROOT / "release_artifacts" / "release_lock.json"
SHA256_RE = re.compile(r"^[a-f0-9]{64}$")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _normalize_rel(path_value: str) -> str:
    text = path_value.replace("\\", "/")
    if text.startswith("release_artifacts/"):
        return text.split("/", 1)[1]
    return text


def _resolve_artifact_path(path_value: str) -> Path:
    candidate = Path(path_value)
    if candidate.is_absolute():
        return candidate
    normalized = path_value.replace("\\", "/")
    if normalized.startswith("release_artifacts/"):
        return ROOT / normalized
    return ROOT / "release_artifacts" / normalized


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify canonical release/evidence pairing")
    parser.add_argument("--release", type=Path)
    parser.add_argument("--evidence", type=Path)
    parser.add_argument("--lock", type=Path, default=LOCK)
    parser.add_argument(
        "--pre-evidence",
        action="store_true",
        help="Verify release lock/hash/hygiene before evidence zip exists",
    )
    args = parser.parse_args()

    lock_path = args.lock
    if not lock_path.exists():
        print(f"FAIL: missing {lock_path}")
        return 1

    lock = json.loads(lock_path.read_text(encoding="utf-8"))
    release = args.release if args.release else _resolve_artifact_path(str(lock["release_zip"]))
    evidence = args.evidence if args.evidence else _resolve_artifact_path(str(lock["evidence_zip"]))

    if not release.exists():
        print(f"FAIL: missing release ZIP: {release}")
        return 1

    if not args.pre_evidence and not evidence.exists():
        print(f"FAIL: missing evidence ZIP: {evidence}")
        return 1

    actual_release = sha256(release)
    if actual_release != lock["release_sha256"]:
        print("FAIL: release hash mismatch")
        print(f"lock:   {lock['release_sha256']}")
        print(f"actual: {actual_release}")
        return 1

    hygiene = run(
        [sys.executable, str(ROOT / "scripts" / "check_source_bundle_hygiene.py"), str(release)],
        cwd=ROOT,
        text=True,
    )
    if hygiene.returncode != 0:
        return hygiene.returncode

    if args.pre_evidence:
        print("PASS: release pre-evidence checks verified")
        return 0

    actual_evidence = sha256(evidence)
    if actual_evidence != lock["evidence_sha256"]:
        print("FAIL: evidence hash mismatch")
        print(f"lock:   {lock['evidence_sha256']}")
        print(f"actual: {actual_evidence}")
        return 1

    with zipfile.ZipFile(evidence) as zf:
        names = set(zf.namelist())
        required = ".validation_logs/validation_summary.json"
        hashes_file = ".validation_logs/release_hashes.json"
        pair_log = ".validation_logs/release_pair_verification.txt"
        if required not in names:
            print(f"FAIL: evidence missing {required}")
            return 1
        if hashes_file not in names:
            print(f"FAIL: evidence missing {hashes_file}")
            return 1
        if pair_log not in names:
            print(f"FAIL: evidence missing {pair_log}")
            return 1
        summary = json.loads(zf.read(required).decode("utf-8"))
        release_hashes = json.loads(zf.read(hashes_file).decode("utf-8"))
        pair_text = zf.read(pair_log).decode("utf-8", errors="replace")

    if summary.get("status") not in {"pass", "pass_with_warnings"}:
        print(f"FAIL: validation summary status: {summary.get('status')}")
        return 1
    if summary.get("components", {}).get("release_pair_verification") != "pass":
        print("FAIL: validation summary release_pair_verification component is not pass")
        return 1
    if "FAIL" in pair_text or "PASS" not in pair_text:
        print("FAIL: evidence release_pair_verification log is not PASS")
        return 1

    expected_release_zip = _normalize_rel(lock["release_zip"])
    expected_evidence_zip = _normalize_rel(lock["evidence_zip"])
    observed_release_zip = _normalize_rel(release_hashes.get("release_zip", ""))
    observed_evidence_zip = _normalize_rel(release_hashes.get("evidence_zip", ""))
    if observed_release_zip != expected_release_zip:
        print("FAIL: evidence internal release_zip mismatch")
        print(f"lock:     {expected_release_zip}")
        print(f"evidence: {observed_release_zip}")
        return 1
    if observed_evidence_zip != expected_evidence_zip:
        print("FAIL: evidence internal evidence_zip mismatch")
        print(f"lock:     {expected_evidence_zip}")
        print(f"evidence: {observed_evidence_zip}")
        return 1
    if release_hashes.get("release_sha256") != lock["release_sha256"]:
        print("FAIL: evidence internal release_sha256 mismatch")
        print(f"lock:     {lock['release_sha256']}")
        print(f"evidence: {release_hashes.get('release_sha256')}")
        return 1
    if "evidence_sha256" in release_hashes:
        evidence_sha = release_hashes.get("evidence_sha256")
        if evidence_sha is None:
            pass
        elif evidence_sha == "external-lock-governed":
            pass
        elif isinstance(evidence_sha, str) and SHA256_RE.fullmatch(evidence_sha):
            pass
        else:
            print("FAIL: evidence internal evidence_sha256 has unsupported format")
            print(f"evidence: {evidence_sha!r}")
            return 1

    print("PASS: release/evidence pair verified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
