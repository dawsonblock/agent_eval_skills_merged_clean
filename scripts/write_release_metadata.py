#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
LOCK = ROOT / "release_artifacts" / "release_lock.json"


def main() -> int:
    lock = json.loads(LOCK.read_text(encoding="utf-8"))
    status = {
        "status": lock["status"],
        "canonical": lock["canonical"],
        "validation_profile": lock["validation_profile"],
        "release_zip": lock["release_zip"],
        "release_sha256": lock["release_sha256"],
        "evidence_zip": lock["evidence_zip"],
        "evidence_sha256": lock["evidence_sha256"],
        "python_version": lock["python_version"],
        "node_version_min": lock["node_version_min"],
        "limitations": [
            "Smoke profile only.",
            "Toolathlon full profile is experimental.",
            "Agent Skills quality warnings remain.",
            "Not production deployment approved.",
        ],
    }
    (ROOT / "RELEASE_STATUS.json").write_text(json.dumps(status, indent=2) + "\n", encoding="utf-8")

    manifest = {
        "release": {
            "name": lock["release_name"],
            "zip": lock["release_zip"],
            "sha256": lock["release_sha256"],
        },
        "evidence": {
            "zip": lock["evidence_zip"],
            "sha256": lock["evidence_sha256"],
        },
    }
    (ROOT / "RELEASE_MANIFEST.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    evidence_md = f"""# Validation Evidence
Canonical release ZIP:
`{lock["release_zip"]}`
Release SHA256:
`{lock["release_sha256"]}`
Canonical evidence ZIP:
`{lock["evidence_zip"]}`
Evidence SHA256:
`{lock["evidence_sha256"]}`
Validation profile:
`{lock["validation_profile"]}`
Status:
`{lock["status"]}`
Limitations:
- Toolathlon smoke profile is release-gated.
- Toolathlon full profile is experimental.
- Agent Skills structural validation is release-gated.
- Agent Skills quality warnings remain.
- This package is not approved for production deployment.
"""
    (ROOT / "VALIDATION_EVIDENCE.md").write_text(evidence_md, encoding="utf-8")

    attestation = f"""# Release Attestation - 2026-05-27
This attestation binds the smoke release artifact to its evidence package.
Release ZIP:
`{lock["release_zip"]}`
Release SHA256:
`{lock["release_sha256"]}`
Evidence ZIP:
`{lock["evidence_zip"]}`
Evidence SHA256:
`{lock["evidence_sha256"]}`
Validation profile:
`{lock["validation_profile"]}`
Status:
`{lock["status"]}`
Scope:
This is a smoke-validated release candidate for local agent-tool evaluation and curated skill packaging.
Non-scope:
- Not a production deployment package.
- Not a full Toolathlon release.
- Not a security-audited production benchmark environment.
"""
    (ROOT / "RELEASE_ATTESTATION_2026-05-27.md").write_text(attestation, encoding="utf-8")

    print("Wrote release metadata files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
