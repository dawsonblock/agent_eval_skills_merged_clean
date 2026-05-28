#!/usr/bin/env python3
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RELEASE_ZIP = ROOT / "release_artifacts" / "agent_eval_skills_merged_clean-pruned-smoke.zip"
DEFAULT_IDENTITY = ROOT / "release_artifacts" / "release_identity.generated.json"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def latest_evidence_zip() -> Path:
    candidates = sorted(
        (ROOT / "release_artifacts").glob("agent_eval_skills_merged_clean-smoke-evidence-*.zip"),
        key=lambda p: p.stat().st_mtime,
    )
    if not candidates:
        raise SystemExit(
            "No smoke evidence ZIP found in release_artifacts/. Run scripts/collect_smoke_evidence.sh first."
        )
    return candidates[-1]


def run_python(script: str, *args: str) -> None:
    cmd = [sys.executable, str(ROOT / script), *args]
    subprocess.run(cmd, check=True, cwd=ROOT)


def main() -> int:
    parser = argparse.ArgumentParser(description="Write lock + synced release metadata from current artifacts")
    parser.add_argument("--release-zip", type=Path, default=DEFAULT_RELEASE_ZIP)
    parser.add_argument("--evidence-zip", type=Path, help="Defaults to latest smoke evidence ZIP")
    parser.add_argument("--release-date", default=datetime.now(timezone.utc).date().isoformat())
    parser.add_argument("--profile", default="smoke")
    parser.add_argument("--python-version", default="3.12")
    parser.add_argument("--node-version-min", default="20")
    parser.add_argument("--status", default="release-candidate")
    parser.add_argument("--identity-out", type=Path, default=DEFAULT_IDENTITY)
    args = parser.parse_args()

    release_zip = args.release_zip
    evidence_zip = args.evidence_zip or latest_evidence_zip()

    if not release_zip.exists():
        raise SystemExit(f"Release ZIP not found: {release_zip}")
    if not evidence_zip.exists():
        raise SystemExit(f"Evidence ZIP not found: {evidence_zip}")

    release_sha = sha256_file(release_zip)
    evidence_sha = sha256_file(evidence_zip)

    run_python(
        "scripts/write_release_lock.py",
        "--release-date",
        args.release_date,
        "--release-zip",
        release_zip.relative_to(ROOT).as_posix(),
        "--release-sha",
        release_sha,
        "--evidence-zip",
        evidence_zip.relative_to(ROOT).as_posix(),
        "--evidence-sha",
        evidence_sha,
        "--profile",
        args.profile,
        "--python-version",
        args.python_version,
        "--node-version-min",
        args.node_version_min,
        "--status",
        args.status,
    )

    run_python("scripts/sync_release_metadata_from_lock.py")
    run_python("scripts/generate_release_manifest.py")
    run_python("scripts/compute_release_identity.py", "--out", str(args.identity_out))

    print("Release metadata synchronized from release_lock.json")
    print(f"release_zip={release_zip.relative_to(ROOT).as_posix()} sha256={release_sha}")
    print(f"evidence_zip={evidence_zip.relative_to(ROOT).as_posix()} sha256={evidence_sha}")
    print(f"identity={args.identity_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
