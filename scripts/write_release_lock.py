#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LOCK = REPO_ROOT / "release_artifacts" / "release_lock.json"


def main() -> int:
    parser = argparse.ArgumentParser(description="Write canonical release_lock.json")
    parser.add_argument("--lock", type=Path, default=DEFAULT_LOCK)
    parser.add_argument("--release-name", default="agent_eval_skills_merged_clean-pruned-smoke")
    parser.add_argument("--release-date", required=True)
    parser.add_argument("--release-zip", required=True)
    parser.add_argument("--release-sha", required=True)
    parser.add_argument("--evidence-zip", required=True)
    parser.add_argument("--evidence-sha", required=True)
    parser.add_argument("--profile", default="smoke")
    parser.add_argument("--python-version", default="3.12")
    parser.add_argument("--node-version-min", default="20")
    parser.add_argument("--status", default="release-candidate")
    args = parser.parse_args()

    payload = {
        "release_name": args.release_name,
        "release_date": args.release_date,
        "release_zip": args.release_zip,
        "release_sha256": args.release_sha,
        "evidence_zip": args.evidence_zip,
        "evidence_sha256": args.evidence_sha,
        "validation_profile": args.profile,
        "python_version": args.python_version,
        "node_version_min": args.node_version_min,
        "status": args.status,
        "canonical": True,
    }

    args.lock.parent.mkdir(parents=True, exist_ok=True)
    args.lock.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {args.lock}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
