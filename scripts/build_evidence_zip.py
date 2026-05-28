#!/usr/bin/env python3
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import zipfile


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LOGS = REPO_ROOT / "release_artifacts" / "validation_logs"
DEFAULT_OUT = (
    REPO_ROOT / "release_artifacts" / "agent_eval_skills_merged_clean-smoke-evidence-2026-05-27.zip"
)
FIXED_DT = (2026, 5, 27, 0, 0, 0)

REQUIRED_FILES = [
    "validation_summary.json",
    "toolforge_summary.json",
    "agent_skills_summary.json",
    "toolathlon_smoke_summary.json",
    "release_hashes.json",
    "environment.json",
    "test_results_root.txt",
    "test_results_toolforge.txt",
    "test_results_agent_skills.txt",
    "test_results_toolathlon.txt",
]


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def write_release_hashes(
    logs_dir: Path,
    release_zip: str,
    release_sha: str,
    evidence_zip: str,
) -> None:
    payload = {
        "release_zip": release_zip,
        "release_sha256": release_sha,
        "evidence_zip": evidence_zip,
        "evidence_sha256": "",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "profile": "smoke",
    }
    output = logs_dir / "release_hashes.json"
    output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def build_zip(logs_dir: Path, out_path: Path) -> str:
    missing = [name for name in REQUIRED_FILES if not (logs_dir / name).exists()]
    if missing:
        missing_str = ", ".join(missing)
        raise SystemExit(f"Missing required validation logs: {missing_str}")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    if out_path.exists():
        out_path.unlink()

    with zipfile.ZipFile(out_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for name in sorted(REQUIRED_FILES):
            src = logs_dir / name
            rel = f"release_artifacts/validation_logs/{name}"
            zi = zipfile.ZipInfo(rel, FIXED_DT)
            zi.external_attr = 0o644 << 16
            zi.compress_type = zipfile.ZIP_DEFLATED
            zf.writestr(zi, src.read_bytes())

    return sha256_of(out_path)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build smoke evidence ZIP from validation logs.")
    parser.add_argument("--logs", type=Path, default=DEFAULT_LOGS, help="Validation logs directory")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT, help="Evidence ZIP output path")
    parser.add_argument("--release-zip", default="agent_eval_skills_merged_clean-pruned-smoke.zip")
    parser.add_argument("--release-sha", required=True)
    args = parser.parse_args()

    logs_dir = args.logs
    logs_dir.mkdir(parents=True, exist_ok=True)

    write_release_hashes(
        logs_dir=logs_dir,
        release_zip=args.release_zip,
        release_sha=args.release_sha,
        evidence_zip=args.out.name,
    )

    evidence_sha = build_zip(logs_dir, args.out)

    release_hashes_path = logs_dir / "release_hashes.json"
    release_hashes = json.loads(release_hashes_path.read_text(encoding="utf-8"))
    release_hashes["evidence_sha256"] = evidence_sha
    release_hashes_path.write_text(json.dumps(release_hashes, indent=2) + "\n", encoding="utf-8")

    print(f"Wrote {args.out}")
    print(f"SHA256: {evidence_sha}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
