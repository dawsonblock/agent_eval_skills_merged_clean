#!/usr/bin/env python3
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LOCK = ROOT / "release_artifacts" / "release_lock.json"
DEFAULT_OUT = ROOT / "release_artifacts" / "release_identity.generated.json"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def latest_evidence_zip(release_artifacts: Path) -> Path:
    candidates = sorted(
        release_artifacts.glob("agent_eval_skills_merged_clean-smoke-evidence-*.zip"),
        key=lambda p: p.stat().st_mtime,
    )
    if not candidates:
        raise SystemExit("No smoke evidence ZIP found in release_artifacts/")
    return candidates[-1]


def main() -> int:
    parser = argparse.ArgumentParser(description="Compute canonical release identity metadata")
    parser.add_argument("--lock", type=Path, default=DEFAULT_LOCK)
    parser.add_argument("--release-zip", type=Path, help="Override canonical release ZIP path")
    parser.add_argument("--evidence-zip", type=Path, help="Override evidence ZIP path")
    parser.add_argument(
        "--wrapper-zip",
        type=Path,
        help="Optional wrapper/source bundle ZIP to hash as uploaded_archive_sha256",
    )
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()

    lock = json.loads(args.lock.read_text(encoding="utf-8")) if args.lock.exists() else {}

    release_zip = args.release_zip or ROOT / lock.get(
        "release_zip", "release_artifacts/agent_eval_skills_merged_clean-pruned-smoke.zip"
    )
    evidence_zip = args.evidence_zip or ROOT / lock.get("evidence_zip", "")
    if not evidence_zip:
        evidence_zip = latest_evidence_zip(ROOT / "release_artifacts")

    if not release_zip.exists():
        raise SystemExit(f"Release ZIP not found: {release_zip}")
    if not evidence_zip.exists():
        raise SystemExit(f"Evidence ZIP not found: {evidence_zip}")

    status_path = ROOT / "RELEASE_STATUS.json"
    status = json.loads(status_path.read_text(encoding="utf-8")) if status_path.exists() else {}

    payload: dict[str, object] = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "release_classification": status.get("release_classification", "SOURCE_BUNDLE"),
        "canonical_release_zip": release_zip.relative_to(ROOT).as_posix(),
        "canonical_release_sha256": sha256_file(release_zip),
        "canonical_release_size_bytes": release_zip.stat().st_size,
        "evidence_zip": evidence_zip.relative_to(ROOT).as_posix(),
        "evidence_sha256": sha256_file(evidence_zip),
        "evidence_size_bytes": evidence_zip.stat().st_size,
        "toolathlon_profile": status.get("toolathlon_profile", lock.get("validation_profile", "smoke")),
        "full_profile_validated": status.get("full_profile_validated", False),
        "production_claim_allowed": status.get("production_claim_allowed", False),
        "python_version": lock.get("python_version", "3.12"),
        "node_version_min": lock.get("node_version_min", "20"),
    }

    if args.wrapper_zip is not None:
        if not args.wrapper_zip.exists():
            raise SystemExit(f"Wrapper ZIP not found: {args.wrapper_zip}")
        payload["uploaded_archive_zip"] = args.wrapper_zip.relative_to(ROOT).as_posix()
        payload["uploaded_archive_sha256"] = sha256_file(args.wrapper_zip)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Wrote {args.out}")
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
