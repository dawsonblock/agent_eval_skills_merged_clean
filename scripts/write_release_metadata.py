#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LOCK = ROOT / "release_artifacts" / "release_lock.json"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Write release metadata files from release_lock.json"
    )
    parser.add_argument(
        "--uploaded-archive",
        type=Path,
        help=(
            "Optional path to final upload wrapper ZIP; if set, its SHA256 is "
            "written to RELEASE_STATUS.uploaded_archive_sha256"
        ),
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    lock = json.loads(LOCK.read_text(encoding="utf-8"))
    status_path = ROOT / "RELEASE_STATUS.json"
    existing_status = {}
    if status_path.exists():
        existing_status = json.loads(status_path.read_text(encoding="utf-8"))

    uploaded_archive_sha = existing_status.get("uploaded_archive_sha256", "")
    uploaded_archive_sha_location = existing_status.get(
        "uploaded_archive_sha256_location", "external .sha256 sidecar"
    )
    if args.uploaded_archive is not None:
        if not args.uploaded_archive.exists():
            raise SystemExit(f"Uploaded archive not found: {args.uploaded_archive}")
        uploaded_archive_sha = sha256_file(args.uploaded_archive)
        uploaded_archive_sha_location = str(args.uploaded_archive.with_suffix(args.uploaded_archive.suffix + ".sha256"))

    status = {
        "status": lock["status"],
        "canonical": lock["canonical"],
        "validation_profile": lock["validation_profile"],
        "release_classification": existing_status.get("release_classification", "SOURCE_BUNDLE"),
        "toolathlon_profile": existing_status.get("toolathlon_profile", lock["validation_profile"]),
        "release_zip": lock["release_zip"],
        "release_sha256": lock["release_sha256"],
        "evidence_zip": lock["evidence_zip"],
        "evidence_sha256": lock["evidence_sha256"],
        "canonical_release_zip": lock["release_zip"],
        "canonical_release_sha256": lock["release_sha256"],
        "uploaded_archive_sha256": uploaded_archive_sha,
        "uploaded_archive_sha256_location": uploaded_archive_sha_location,
        "python_version": lock["python_version"],
        "node_version_min": lock["node_version_min"],
        "limitations": [
            "Smoke profile only.",
            "Toolathlon full profile is experimental.",
            "Agent Skills quality warnings remain.",
            "Not production deployment approved.",
        ],
    }
    status_path.write_text(json.dumps(status, indent=2) + "\n", encoding="utf-8")

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
    (ROOT / "RELEASE_MANIFEST.json").write_text(
        json.dumps(manifest, indent=2) + "\n",
        encoding="utf-8",
    )

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
This is a smoke-validated release candidate for local agent-tool evaluation and
curated skill packaging.
Non-scope:
- Not a production deployment package.
- Not a full Toolathlon release.
- Not a security-audited production benchmark environment.
"""
    (ROOT / "RELEASE_ATTESTATION_2026-05-27.md").write_text(attestation, encoding="utf-8")

    release_zip_path = ROOT / "release_artifacts" / lock["release_zip"]
    evidence_zip_path = ROOT / "release_artifacts" / lock["evidence_zip"]
    identity_payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "release_classification": status["release_classification"],
        "canonical_release_zip": lock["release_zip"],
        "canonical_release_sha256": lock["release_sha256"],
        "canonical_release_size_bytes": release_zip_path.stat().st_size if release_zip_path.exists() else 0,
        "evidence_zip": lock["evidence_zip"],
        "evidence_sha256": lock["evidence_sha256"],
        "evidence_size_bytes": evidence_zip_path.stat().st_size if evidence_zip_path.exists() else 0,
        "toolathlon_profile": status["toolathlon_profile"],
        "full_profile_validated": False,
        "production_claim_allowed": False,
        "python_version": lock["python_version"],
        "node_version_min": lock["node_version_min"],
        "uploaded_archive_sha256": uploaded_archive_sha,
        "uploaded_archive_sha256_location": uploaded_archive_sha_location,
    }
    (ROOT / "release_artifacts" / "release_identity.generated.json").write_text(
        json.dumps(identity_payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    attestation_env = "\n".join(
        [
            "# Canonical attested release/evidence pair constants.",
            "# Scripts should source this file to avoid drift across gates.",
            "",
            f"EXPECTED_RELEASE_NAME={lock['release_zip']}",
            f"EXPECTED_RELEASE_SHA={lock['release_sha256']}",
            f"EXPECTED_EVIDENCE_NAME={lock['evidence_zip']}",
            f"EXPECTED_EVIDENCE_SHA={lock['evidence_sha256']}",
            "",
            "# Canonical smoke-profile policy constants.",
            "EXPECTED_TOOLATHLON_PROFILE=smoke",
            "EXPECTED_MCP_PACKAGE_COUNT=2",
            "EXPECTED_SMOKE_TARGETS=rail_12306,filesystem",
            "EXPECTED_FULL_PROFILE_VALIDATED=false",
            f"EXPECTED_PYTHON_VERSION={lock['python_version']}",
            "MAX_EVIDENCE_AGE_DAYS=30",
            "",
        ]
    )
    (ROOT / "scripts" / "canonical_release_attestation.env").write_text(
        attestation_env,
        encoding="utf-8",
    )

    print("Wrote release metadata files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
