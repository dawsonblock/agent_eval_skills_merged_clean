#!/usr/bin/env python3
"""Sync canonical release artifacts from release_artifacts/ to dist/release/.

Reads release_lock.json for the canonical release/evidence pair names and hashes,
verifies integrity, deletes stale ZIPs from dist/release/, copies the canonical
pair, and regenerates SHA256SUMS.txt.
"""
from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOCK = ROOT / "release_artifacts" / "release_lock.json"
SRC = ROOT / "release_artifacts"
DST = ROOT / "dist" / "release"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    if not LOCK.exists():
        raise SystemExit(f"Missing release lock: {LOCK}")

    data = json.loads(LOCK.read_text(encoding="utf-8"))

    release_name = data.get("release_zip")
    evidence_name = data.get("evidence_zip")
    release_sha = data.get("release_sha256")
    evidence_sha = data.get("evidence_sha256")

    missing = [
        key for key, value in {
            "release_zip": release_name,
            "evidence_zip": evidence_name,
            "release_sha256": release_sha,
            "evidence_sha256": evidence_sha,
        }.items()
        if not value
    ]
    if missing:
        raise SystemExit(f"release_lock.json missing keys: {missing}")

    release_src = SRC / release_name
    evidence_src = SRC / evidence_name

    if not release_src.exists():
        raise SystemExit(f"Missing canonical release ZIP: {release_src}")
    if not evidence_src.exists():
        raise SystemExit(f"Missing canonical evidence ZIP: {evidence_src}")

    actual_release_sha = sha256_file(release_src)
    actual_evidence_sha = sha256_file(evidence_src)

    if actual_release_sha != release_sha:
        raise SystemExit(
            f"Release hash mismatch:\n"
            f"expected {release_sha}\n"
            f"actual   {actual_release_sha}"
        )
    if actual_evidence_sha != evidence_sha:
        raise SystemExit(
            f"Evidence hash mismatch:\n"
            f"expected {evidence_sha}\n"
            f"actual   {actual_evidence_sha}"
        )

    DST.mkdir(parents=True, exist_ok=True)

    # Delete stale ZIPs first to prevent old artifacts from surviving
    stale_zips = list(DST.glob("*.zip"))
    for old_zip in stale_zips:
        old_zip.unlink()

    shutil.copy2(release_src, DST / release_name)
    shutil.copy2(evidence_src, DST / evidence_name)

    sums = DST / "SHA256SUMS.txt"
    sums.write_text(
        f"{release_sha}  {release_name}\n"
        f"{evidence_sha}  {evidence_name}\n",
        encoding="utf-8",
    )

    print(f"[sync] copied {release_name}")
    print(f"[sync] copied {evidence_name}")
    print(f"[sync] wrote SHA256SUMS.txt")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
