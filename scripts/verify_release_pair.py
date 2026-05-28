#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from subprocess import run
import zipfile


ROOT = Path(__file__).resolve().parents[1]
LOCK = ROOT / "release_artifacts" / "release_lock.json"


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


def main() -> int:
    if not LOCK.exists():
        print(f"FAIL: missing {LOCK}")
        return 1

    lock = json.loads(LOCK.read_text(encoding="utf-8"))
    release = ROOT / "release_artifacts" / lock["release_zip"]
    evidence = ROOT / "release_artifacts" / lock["evidence_zip"]

    if not release.exists():
        print(f"FAIL: missing release ZIP: {release}")
        return 1
    if not evidence.exists():
        print(f"FAIL: missing evidence ZIP: {evidence}")
        return 1

    actual_release = sha256(release)
    actual_evidence = sha256(evidence)
    if actual_release != lock["release_sha256"]:
        print("FAIL: release hash mismatch")
        print(f"lock:   {lock['release_sha256']}")
        print(f"actual: {actual_release}")
        return 1
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
    hygiene = run(
        [sys.executable, str(ROOT / "scripts" / "check_source_bundle_hygiene.py"), str(release)],
        cwd=ROOT,
        text=True,
    )
    if hygiene.returncode != 0:
        return hygiene.returncode

    print("PASS: release/evidence pair verified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
