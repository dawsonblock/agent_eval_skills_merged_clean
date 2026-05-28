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
        if required not in names:
            print(f"FAIL: evidence missing {required}")
            return 1
        summary = json.loads(zf.read(required).decode("utf-8"))
    if summary.get("status") not in {"pass", "pass_with_warnings"}:
        print(f"FAIL: validation summary status: {summary.get('status')}")
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
