#!/usr/bin/env python3
from __future__ import annotations

import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LOCK = ROOT / "release_artifacts" / "release_lock.json"
HASH_RE = re.compile(r"\b[a-f0-9]{64}\b")
CHECK_FILES = [
    ROOT / "RELEASE_STATUS.json",
    ROOT / "RELEASE_MANIFEST.json",
    ROOT / "VALIDATION_EVIDENCE.md",
    ROOT / "RELEASE_ATTESTATION_2026-05-27.md",
    ROOT / "RELEASE_EVIDENCE_MANIFEST_2026-05-27.json",
    ROOT / "release_artifacts" / "release_identity.generated.json",
    ROOT / "release_artifacts" / "release_lock.json",
    ROOT / "release_artifacts" / "validation_logs" / "release_hashes.json",
    ROOT / "scripts" / "canonical_release_attestation.env",
]


def main() -> int:
    if not LOCK.exists():
        print(f"FAIL: missing {LOCK}")
        return 1

    lock = json.loads(LOCK.read_text(encoding="utf-8"))
    allowed = {
        h
        for h in [
            lock.get("release_sha256", ""),
            lock.get("evidence_sha256", ""),
        ]
        if h
    }

    bad: list[tuple[str, str]] = []
    for path in CHECK_FILES:
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for digest in HASH_RE.findall(text):
            if allowed and digest not in allowed:
                bad.append((str(path.relative_to(ROOT)), digest))

    if bad:
        print("FAIL: conflicting hashes found")
        for rel, digest in bad:
            print(f"{rel}: {digest}")
        return 1

    print("PASS: release hash references are consistent")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
