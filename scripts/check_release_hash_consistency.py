#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LOCK = REPO_ROOT / "release_artifacts" / "release_lock.json"


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def find_required(text: str, pattern: str, label: str) -> str:
    m = re.search(pattern, text)
    if not m:
        raise ValueError(f"Missing {label}")
    return m.group(1)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Check hash consistency across release metadata files"
    )
    parser.add_argument("--lock", type=Path, default=DEFAULT_LOCK)
    args = parser.parse_args()

    lock = read_json(args.lock)
    release_sha = lock["release_sha256"]
    evidence_sha = lock["evidence_sha256"]
    release_zip = lock["release_zip"]
    evidence_zip = lock["evidence_zip"]

    mismatches: list[str] = []

    status_path = REPO_ROOT / "RELEASE_STATUS.json"
    if status_path.exists():
        status = read_json(status_path)
        if status.get("canonical_release_zip") != release_zip:
            mismatches.append("RELEASE_STATUS.json canonical_release_zip mismatch")
        if status.get("canonical_release_sha256") != release_sha:
            mismatches.append("RELEASE_STATUS.json canonical_release_sha256 mismatch")

    _ = release_zip

    readme_path = REPO_ROOT / "README.md"
    if readme_path.exists():
        readme = readme_path.read_text(encoding="utf-8")
        if release_zip not in readme or release_sha not in readme:
            mismatches.append("README.md missing release ZIP/hash reference")
        if evidence_zip not in readme or evidence_sha not in readme:
            mismatches.append("README.md missing evidence ZIP/hash reference")

    validation_path = REPO_ROOT / "VALIDATION_EVIDENCE.md"
    if validation_path.exists():
        text = validation_path.read_text(encoding="utf-8")
        if release_sha not in text:
            mismatches.append("VALIDATION_EVIDENCE.md missing release SHA")
        if evidence_sha not in text:
            mismatches.append("VALIDATION_EVIDENCE.md missing evidence SHA")

    attestation_path = REPO_ROOT / "RELEASE_ATTESTATION_2026-05-27.md"
    if attestation_path.exists():
        text = attestation_path.read_text(encoding="utf-8")
        att_release = find_required(
            text,
            r"`[^`]*agent_eval_skills_merged_clean-pruned-smoke\.zip` \| `([a-f0-9]{64})`",
            "release attestation hash",
        )
        att_evidence = find_required(
            text,
            r"`[^`]*agent_eval_skills_merged_clean-smoke-evidence-[^`]+` \| `([a-f0-9]{64})`",
            "evidence attestation hash",
        )
        if att_release != release_sha:
            mismatches.append("RELEASE_ATTESTATION_2026-05-27.md release hash mismatch")
        if att_evidence != evidence_sha:
            mismatches.append("RELEASE_ATTESTATION_2026-05-27.md evidence hash mismatch")

    if mismatches:
        print("FAIL: release metadata drift detected")
        for item in mismatches:
            print(f"- {item}")
        return 1

    print("PASS: all release references match release_artifacts/release_lock.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
