#!/usr/bin/env python3
"""Write release_artifacts/validation_logs/release_hashes.json from release_lock.json."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOCK_PATH = ROOT / "release_artifacts" / "release_lock.json"
OUT_PATH = ROOT / "release_artifacts" / "validation_logs" / "release_hashes.json"


def main() -> int:
    if not LOCK_PATH.exists():
        print(f"FAIL: {LOCK_PATH} not found")
        return 1

    lock = json.loads(LOCK_PATH.read_text(encoding="utf-8"))

    hashes = {
        "release_zip": lock.get("release_zip", ""),
        "release_sha256": lock.get("release_sha256", ""),
        "evidence_zip": lock.get("evidence_zip", ""),
        "evidence_sha256": "external-lock-governed",
        "profile": lock.get("validation_profile", "smoke"),
        "final_evidence_sha256_authority": "release_artifacts/release_lock.json",
    }

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(hashes, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {OUT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
