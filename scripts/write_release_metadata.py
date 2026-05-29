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
    release_zip_name = str(lock["release_zip"])
    evidence_zip_name = str(lock["evidence_zip"])

    uploaded_archive_sha = None
    uploaded_archive_sha_location = "external sidecar .sha256 file"
    if args.uploaded_archive is not None:
        if not args.uploaded_archive.exists():
            raise SystemExit(f"Uploaded archive not found: {args.uploaded_archive}")
        uploaded_archive_sha = sha256_file(args.uploaded_archive)
        uploaded_archive_sha_location = str(
            args.uploaded_archive.with_suffix(args.uploaded_archive.suffix + ".sha256")
        )

    status = {
        "status": lock["status"],
        "release_classification": "SOURCE_BUNDLE_WITH_CANONICAL_SMOKE_RELEASE",
        "toolathlon_profile": "smoke",
        "canonical": lock["canonical"],
        "validation_profile": lock["validation_profile"],
        "release_zip": release_zip_name,
        "release_sha256": lock["release_sha256"],
        "evidence_zip": evidence_zip_name,
        "evidence_sha256": lock["evidence_sha256"],
        "canonical_release_zip": release_zip_name,
        "canonical_release_sha256": lock["release_sha256"],
        "canonical_evidence_zip": evidence_zip_name,
        "canonical_evidence_sha256": lock["evidence_sha256"],
        "uploaded_archive_sha256": uploaded_archive_sha,
        "uploaded_archive_sha256_location": uploaded_archive_sha_location,
        "limitations": [
            "Smoke profile only.",
            "Toolathlon full profile is experimental.",
            "Agent Skills quality warnings remain.",
            "Not production deployment approved.",
            "Not security-audited.",
        ],
    }
    status_path = ROOT / "RELEASE_STATUS.json"
    status_path.write_text(json.dumps(status, indent=2) + "\n", encoding="utf-8")

    manifest = {
        "release": {
            "name": lock["release_name"],
            "zip": release_zip_name,
            "sha256": lock["release_sha256"],
        },
        "evidence": {
            "zip": evidence_zip_name,
            "sha256": lock["evidence_sha256"],
        },
    }
    (ROOT / "RELEASE_MANIFEST.json").write_text(
        json.dumps(manifest, indent=2) + "\n",
        encoding="utf-8",
    )

    evidence_md = f"""# Validation Evidence
Canonical release ZIP:
`{release_zip_name}`
Release SHA256:
`{lock["release_sha256"]}`
Canonical evidence ZIP:
`{evidence_zip_name}`
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
- This package is not security-audited.
"""
    (ROOT / "VALIDATION_EVIDENCE.md").write_text(evidence_md, encoding="utf-8")

    attestation = f"""# Release Attestation - 2026-05-27
This attestation binds the smoke release artifact to its evidence package.
Release ZIP:
`{release_zip_name}`
Release SHA256:
`{lock["release_sha256"]}`
Evidence ZIP:
`{evidence_zip_name}`
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
- Not a security-audited package.
"""
    (ROOT / "RELEASE_ATTESTATION_2026-05-27.md").write_text(attestation, encoding="utf-8")

    release_zip_path = ROOT / "release_artifacts" / release_zip_name
    evidence_zip_path = ROOT / "release_artifacts" / evidence_zip_name
    identity_payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "release_classification": "SOURCE_BUNDLE_WITH_CANONICAL_SMOKE_RELEASE",
        "canonical_release_zip": release_zip_name,
        "canonical_release_sha256": lock["release_sha256"],
        "canonical_release_size_bytes": (
            release_zip_path.stat().st_size if release_zip_path.exists() else 0
        ),
        "evidence_zip": evidence_zip_name,
        "evidence_sha256": lock["evidence_sha256"],
        "evidence_size_bytes": (
            evidence_zip_path.stat().st_size if evidence_zip_path.exists() else 0
        ),
        "toolathlon_profile": "smoke",
        "full_profile_validated": False,
        "production_claim_allowed": False,
        "release_identity": "external-lock-governed",
        "canonical_lock_file": "release_artifacts/release_lock.json",
        "note": (
            "Final release and evidence SHA256 values are stored "
            "outside this ZIP in the release lock."
        ),
        "python_version": lock.get("python_version", ""),
        "node_version_min": lock.get("node_version_min", ""),
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
            f"EXPECTED_RELEASE_NAME={release_zip_name}",
            f"EXPECTED_RELEASE_SHA={lock['release_sha256']}",
            f"EXPECTED_EVIDENCE_NAME={evidence_zip_name}",
            f"EXPECTED_EVIDENCE_SHA={lock['evidence_sha256']}",
            "",
            "# Canonical smoke-profile policy constants.",
            "EXPECTED_TOOLATHLON_PROFILE=smoke",
            "EXPECTED_MCP_PACKAGE_COUNT=2",
            "EXPECTED_SMOKE_TARGETS=rail_12306,filesystem",
            "EXPECTED_FULL_PROFILE_VALIDATED=false",
            f"EXPECTED_PYTHON_VERSION={lock.get('python_version', '')}",
            "MAX_EVIDENCE_AGE_DAYS=30",
            "",
        ]
    )
    (ROOT / "scripts" / "canonical_release_attestation.env").write_text(
        attestation_env,
        encoding="utf-8",
    )

    evidence_manifest = {
        "repository": "agent_eval_skills_merged_clean",
        "branch": "main",
        "attestation_event_date": lock.get("release_date", "2026-05-27"),
        "workspace_classification": "SOURCE_BUNDLE_WITH_CANONICAL_SMOKE_RELEASE",
        "release_zip": release_zip_name,
        "release_zip_sha256": lock["release_sha256"],
        "evidence_zip": evidence_zip_name,
        "evidence_zip_sha256": lock["evidence_sha256"],
        "validated_scope": [
            "ToolForge",
            "Agent Skills",
            "Toolathlon smoke profile",
        ],
        "not_release_validated": [
            "Full Toolathlon profile",
            "all task material",
            "full MCP server set",
            "production deployment",
            "hostile-code safety",
        ],
        "archive": {
            "path": release_zip_name,
            "sha256": lock["release_sha256"],
        },
        "archive_sha256": lock["release_sha256"],
    }
    (ROOT / "RELEASE_EVIDENCE_MANIFEST_2026-05-27.json").write_text(
        json.dumps(evidence_manifest, indent=2) + "\n",
        encoding="utf-8",
    )

    print("Wrote release metadata files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
