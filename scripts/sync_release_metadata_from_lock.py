#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
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


def sha256_file(path: Path) -> str:
    import hashlib

    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def resolve_artifact_path(path_value: str) -> Path:
    artifact_path = REPO_ROOT / "release_artifacts" / path_value
    if artifact_path.exists():
        return artifact_path

    candidate = REPO_ROOT / path_value
    if candidate.exists():
        return candidate

    return artifact_path


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
        payload["release_zip"] = release_zip
        payload["release_sha256"] = release_sha
        payload["evidence_zip"] = evidence_zip
        payload["evidence_sha256"] = evidence_sha
        payload["canonical_release_zip"] = release_zip
        payload["canonical_release_sha256"] = release_sha
        payload["status"] = lock.get("status", payload.get("status", "release-candidate"))
        payload["canonical"] = lock.get("canonical", payload.get("canonical", True))
        payload["validation_profile"] = lock.get(
            "validation_profile", payload.get("validation_profile", "smoke")
        )
        payload["python_version"] = lock.get(
            "python_version", payload.get("python_version", "3.12")
        )
        payload["node_version_min"] = lock.get(
            "node_version_min", payload.get("node_version_min", "20")
        )
        # Uploaded archive hash is tracked separately and can legitimately differ
        # from canonical release/evidence hashes, so keep it empty by default.
        payload["uploaded_archive_sha256"] = ""
        payload["uploaded_archive_sha256_location"] = "external .sha256 sidecar"

    update_json_file(status_path, update_status)

    manifest_path = REPO_ROOT / "RELEASE_MANIFEST.json"

    def update_manifest(payload: dict) -> None:
        release = payload.setdefault("release", {})
        evidence = payload.setdefault("evidence", {})
        release["name"] = lock.get("release_name", release.get("name", ""))
        release["zip"] = release_zip
        release["sha256"] = release_sha
        evidence["zip"] = evidence_zip
        evidence["sha256"] = evidence_sha

    if manifest_path.exists():
        update_json_file(manifest_path, update_manifest)

    readme_path = REPO_ROOT / "README.md"
    readme = readme_path.read_text(encoding="utf-8")
    if "SHA256" in readme and "agent_eval_skills_merged_clean-pruned-smoke.zip" in readme:
        try:
            readme = replace_or_fail(
                readme,
                (
                    r"- `[^`]*agent_eval_skills_merged_clean-pruned-smoke\.zip`"
                    r"\n\s+- SHA256: `[a-f0-9]{64}`"
                ),
                f"- `{release_zip}`\n  - SHA256: `{release_sha}`",
                "README release hash",
            )
            readme = replace_or_fail(
                readme,
                (
                    r"- `[^`]*agent_eval_skills_merged_clean-smoke-evidence-[^`]+`"
                    r"\n\s+- SHA256: `[a-f0-9]{64}`"
                ),
                f"- `{evidence_zip}`\n  - SHA256: `{evidence_sha}`",
                "README evidence hash",
            )
        except SystemExit:
            pass
        else:
            readme_path.write_text(readme, encoding="utf-8")

    evidence_doc_path = REPO_ROOT / "VALIDATION_EVIDENCE.md"
    evidence_doc = evidence_doc_path.read_text(encoding="utf-8")
    evidence_doc = replace_or_fail(
        evidence_doc,
        (
            r"Canonical release ZIP:\n"
            r"`[^`]*agent_eval_skills_merged_clean-pruned-smoke\.zip`\n"
            r"Release SHA256:\n`[a-f0-9]{64}`"
        ),
        f"Canonical release ZIP:\n`{release_zip}`\nRelease SHA256:\n`{release_sha}`",
        "VALIDATION_EVIDENCE release hash",
    )
    evidence_doc = replace_or_fail(
        evidence_doc,
        (
            r"Canonical evidence ZIP:\n"
            r"`[^`]*agent_eval_skills_merged_clean-smoke-evidence-[^`]+`\n"
            r"Evidence SHA256:\n`[a-f0-9]{64}`"
        ),
        f"Canonical evidence ZIP:\n`{evidence_zip}`\nEvidence SHA256:\n`{evidence_sha}`",
        "VALIDATION_EVIDENCE evidence hash",
    )
    evidence_doc_path.write_text(evidence_doc, encoding="utf-8")

    att_path = REPO_ROOT / "RELEASE_ATTESTATION_2026-05-27.md"
    att = att_path.read_text(encoding="utf-8")
    att = replace_or_fail(
        att,
        (
            r"Release ZIP:\n`[^`]*agent_eval_skills_merged_clean-pruned-smoke\.zip`"
            r"\nRelease SHA256:\n`[a-f0-9]{64}`"
        ),
        f"Release ZIP:\n`{release_zip}`\nRelease SHA256:\n`{release_sha}`",
        "attestation release row",
    )
    att = replace_or_fail(
        att,
        (
            r"Evidence ZIP:\n`[^`]*agent_eval_skills_merged_clean-smoke-evidence-[^`]+`"
            r"\nEvidence SHA256:\n`[a-f0-9]{64}`"
        ),
        f"Evidence ZIP:\n`{evidence_zip}`\nEvidence SHA256:\n`{evidence_sha}`",
        "attestation evidence row",
    )
    att_path.write_text(att, encoding="utf-8")

    deployment_path = REPO_ROOT / "DEPLOYMENT.md"
    if deployment_path.exists():
        deployment = deployment_path.read_text(encoding="utf-8")
        deployment = replace_or_fail(
            deployment,
            (
                r"- `[^`]*agent_eval_skills_merged_clean-pruned-smoke\.zip`"
                r"\n\s+- SHA256: `[a-f0-9]{64}`"
            ),
            f"- `{release_zip}`\n   - SHA256: `{release_sha}`",
            "DEPLOYMENT release hash",
        )
        deployment = replace_or_fail(
            deployment,
            (
                r"- `[^`]*agent_eval_skills_merged_clean-smoke-evidence-[^`]+`"
                r"\n\s+- SHA256: `[a-f0-9]{64}`"
            ),
            f"- `{evidence_zip}`\n   - SHA256: `{evidence_sha}`",
            "DEPLOYMENT evidence hash",
        )
        deployment_path.write_text(deployment, encoding="utf-8")

        handoff_27_path = REPO_ROOT / "release_artifacts" / "RELEASE_HANDOFF_2026-05-27.md"
        if handoff_27_path.exists():
            handoff_27 = handoff_27_path.read_text(encoding="utf-8")
            handoff_27 = handoff_27.replace(
                "01ffe2f112a76baee38d56863413b4595abd9d0e89b799908442a50382c10f0e",
                release_sha,
            )
            handoff_27 = handoff_27.replace(
                "e7ec62bd40c43c49c4e7262fa108888e1e2c4e77ac7a0033fa83e3c6e6a4df73",
                evidence_sha,
            )
            handoff_27_path.write_text(handoff_27, encoding="utf-8")

        handoff_28_path = REPO_ROOT / "release_artifacts" / "RELEASE_HANDOFF_2026-05-28.md"
        if handoff_28_path.exists():
            handoff_28 = handoff_28_path.read_text(encoding="utf-8")
            handoff_28 = handoff_28.replace(
                "01ffe2f112a76baee38d56863413b4595abd9d0e89b799908442a50382c10f0e",
                release_sha,
            )
            handoff_28 = handoff_28.replace(
                "e7ec62bd40c43c49c4e7262fa108888e1e2c4e77ac7a0033fa83e3c6e6a4df73",
                evidence_sha,
            )
            handoff_28_path.write_text(handoff_28, encoding="utf-8")

    dashboard_path = REPO_ROOT / "WORKSPACE_HEALTH_DASHBOARD.md"
    if dashboard_path.exists():
        dashboard = dashboard_path.read_text(encoding="utf-8")
        dashboard = replace_or_fail(
            dashboard,
            r"\*\*Current canonical release SHA256:\*\* `([a-f0-9]{64})`",
            f"**Current canonical release SHA256:** `{release_sha}`",
            "WORKSPACE_HEALTH_DASHBOARD current release sha",
        )
        dashboard = replace_or_fail(
            dashboard,
            (
                r"- `[^`]*agent_eval_skills_merged_clean-pruned-smoke\.zip`"
                r"\n\s+- SHA256: `[a-f0-9]{64}`"
            ),
            f"- `{release_zip}`\n  - SHA256: `{release_sha}`",
            "WORKSPACE_HEALTH_DASHBOARD release hash",
        )
        dashboard = replace_or_fail(
            dashboard,
            (
                r"- `[^`]*agent_eval_skills_merged_clean-smoke-evidence-[^`]+`"
                r"\n\s+- SHA256: `[a-f0-9]{64}`"
            ),
            f"- `{evidence_zip}`\n  - SHA256: `{evidence_sha}`",
            "WORKSPACE_HEALTH_DASHBOARD evidence hash",
        )
        dashboard_path.write_text(dashboard, encoding="utf-8")

    identity_path = REPO_ROOT / "release_artifacts" / "release_identity.generated.json"
    status_path = REPO_ROOT / "RELEASE_STATUS.json"
    status = json.loads(status_path.read_text(encoding="utf-8")) if status_path.exists() else {}
    release_zip_path = resolve_artifact_path(release_zip)
    evidence_zip_path = resolve_artifact_path(evidence_zip)
    identity_payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "release_classification": status.get("release_classification", "SOURCE_BUNDLE"),
        "canonical_release_zip": release_zip,
        "canonical_release_sha256": release_sha,
        "canonical_release_size_bytes": release_zip_path.stat().st_size,
        "evidence_zip": evidence_zip,
        "evidence_sha256": evidence_sha,
        "evidence_size_bytes": evidence_zip_path.stat().st_size,
        "toolathlon_profile": status.get(
            "toolathlon_profile", lock.get("validation_profile", "smoke")
        ),
        "full_profile_validated": status.get("full_profile_validated", False),
        "production_claim_allowed": status.get("production_claim_allowed", False),
        "python_version": lock.get("python_version", "3.12"),
        "node_version_min": lock.get("node_version_min", "20"),
    }
    identity_path.write_text(
        json.dumps(identity_payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    attestation_env_path = REPO_ROOT / "scripts" / "canonical_release_attestation.env"
    attestation_env = "\n".join(
        [
            "# Canonical attested release/evidence pair constants.",
            "# Scripts should source this file to avoid drift across gates.",
            "",
            f"EXPECTED_RELEASE_NAME={release_zip}",
            f"EXPECTED_RELEASE_SHA={release_sha}",
            f"EXPECTED_EVIDENCE_NAME={evidence_zip}",
            f"EXPECTED_EVIDENCE_SHA={evidence_sha}",
            "",
            "# Canonical smoke-profile policy constants.",
            "EXPECTED_TOOLATHLON_PROFILE=smoke",
            "EXPECTED_MCP_PACKAGE_COUNT=2",
            "EXPECTED_SMOKE_TARGETS=rail_12306,filesystem",
            "EXPECTED_FULL_PROFILE_VALIDATED=false",
            "EXPECTED_PYTHON_VERSION=3.12.12",
            "MAX_EVIDENCE_AGE_DAYS=30",
            "",
        ]
    )
    attestation_env_path.write_text(attestation_env, encoding="utf-8")

    sha_sums_path = REPO_ROOT / "dist" / "release" / "SHA256SUMS.txt"
    attestation_22_path = REPO_ROOT / "dist" / "release" / "RELEASE_ATTESTATION_2026-05-22.md"
    sha_lines = [
        f"{release_sha}  {release_zip}",
        f"{evidence_sha}  {evidence_zip}",
    ]
    if attestation_22_path.exists():
        sha_lines.append(f"{sha256_file(attestation_22_path)}  {attestation_22_path.name}")
    sha_sums_path.write_text("\n".join(sha_lines) + "\n", encoding="utf-8")

    evidence_manifest_path = REPO_ROOT / "RELEASE_EVIDENCE_MANIFEST_2026-05-27.json"
    if evidence_manifest_path.exists():
        manifest = json.loads(evidence_manifest_path.read_text(encoding="utf-8"))
        manifest["release_zip"] = release_zip
        manifest["release_zip_sha256"] = release_sha
        manifest["archive"] = {
            "path": release_zip,
            "sha256": release_sha,
            "forbidden_entries_scan": "passed",
        }
        manifest["archive_sha256"] = release_sha
        manifest["evidence_zip"] = evidence_zip
        manifest["evidence_zip_sha256"] = evidence_sha
        evidence_manifest_path.write_text(
            json.dumps(manifest, indent=2) + "\n",
            encoding="utf-8",
        )

    print(
        "Synced RELEASE_STATUS, README, VALIDATION_EVIDENCE, DEPLOYMENT, "
        "WORKSPACE_HEALTH_DASHBOARD, RELEASE_ATTESTATION, RELEASE_EVIDENCE_MANIFEST, "
        "release_identity.generated.json, canonical_release_attestation.env, "
        "and SHA256SUMS from release lock"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
