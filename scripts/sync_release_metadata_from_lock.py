#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LOCK = REPO_ROOT / "release_artifacts" / "release_lock.json"


def update_json_file(path: Path, updater) -> None:
    payload = json.loads(path.read_text(encoding="utf-8"))
    updater(payload)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def replace_or_fail(text: str, pattern: str, repl: str, label: str) -> str:
    new_text, count = re.subn(pattern, repl, text, flags=re.MULTILINE)
    if count == 0:
        raise SystemExit(f"Could not update {label}; pattern not found")
    return new_text


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Sync release metadata files from release_lock.json"
    )
    parser.add_argument("--lock", type=Path, default=DEFAULT_LOCK)
    args = parser.parse_args()

    lock = json.loads(args.lock.read_text(encoding="utf-8"))
    release_zip = lock["release_zip"]
    release_sha = lock["release_sha256"]
    evidence_zip = lock["evidence_zip"]
    evidence_sha = lock["evidence_sha256"]

    status_path = REPO_ROOT / "RELEASE_STATUS.json"

    def update_status(payload: dict) -> None:
        payload["canonical_release_zip"] = release_zip
        payload["canonical_release_sha256"] = release_sha

    update_json_file(status_path, update_status)

    readme_path = REPO_ROOT / "README.md"
    readme = readme_path.read_text(encoding="utf-8")
    readme = replace_or_fail(
        readme,
        r"- `agent_eval_skills_merged_clean-pruned-smoke\.zip`\n\s+- SHA256: `[a-f0-9]{64}`",
        f"- `{release_zip}`\n  - SHA256: `{release_sha}`",
        "README release hash",
    )
    readme = replace_or_fail(
        readme,
        r"- `agent_eval_skills_merged_clean-smoke-evidence-[^`]+`\n\s+- SHA256: `[a-f0-9]{64}`",
        f"- `{evidence_zip}`\n  - SHA256: `{evidence_sha}`",
        "README evidence hash",
    )
    readme_path.write_text(readme, encoding="utf-8")

    evidence_doc_path = REPO_ROOT / "VALIDATION_EVIDENCE.md"
    evidence_doc = evidence_doc_path.read_text(encoding="utf-8")
    evidence_doc = replace_or_fail(
        evidence_doc,
        r"- `agent_eval_skills_merged_clean-pruned-smoke\.zip`\n\s+- SHA256: `[a-f0-9]{64}`",
        f"- `{release_zip}`\n   - SHA256: `{release_sha}`",
        "VALIDATION_EVIDENCE release hash",
    )
    evidence_doc = replace_or_fail(
        evidence_doc,
        r"- `agent_eval_skills_merged_clean-smoke-evidence-[^`]+`\n\s+- SHA256: `[a-f0-9]{64}`",
        f"- `{evidence_zip}`\n   - SHA256: `{evidence_sha}`",
        "VALIDATION_EVIDENCE evidence hash",
    )
    evidence_doc_path.write_text(evidence_doc, encoding="utf-8")

    att_path = REPO_ROOT / "RELEASE_ATTESTATION_2026-05-27.md"
    att = att_path.read_text(encoding="utf-8")
    att = replace_or_fail(
        att,
        r"\| `agent_eval_skills_merged_clean-pruned-smoke\.zip` \| `[a-f0-9]{64}` \|",
        f"| `{release_zip}` | `{release_sha}` |",
        "attestation release row",
    )
    att = replace_or_fail(
        att,
        r"\| `agent_eval_skills_merged_clean-smoke-evidence-[^`]+` \| `[a-f0-9]{64}` \|",
        f"| `{evidence_zip}` | `{evidence_sha}` |",
        "attestation evidence row",
    )
    att_path.write_text(att, encoding="utf-8")

    print(
        "Synced RELEASE_STATUS, README, VALIDATION_EVIDENCE, and "
        "RELEASE_ATTESTATION from release lock"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
