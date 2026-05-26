#!/usr/bin/env python3
"""Verify manifest hash agreement inside an evidence zip."""

from __future__ import annotations

import json
import sys
import zipfile
from datetime import datetime, timezone


def main() -> int:
    if len(sys.argv) != 6 + 1:
        raise SystemExit(
            "usage: verify_manifest_hash_agreement.py "
            "<zip_path> <release_name> <release_sha> "
            "<evidence_name> <evidence_sha> <max_age_days>"
        )

    (
        zip_path,
        exp_release_name,
        exp_release_sha,
        exp_evidence_name,
        exp_evidence_sha,
        max_age_days,
    ) = sys.argv[1:]
    max_age_days_int = int(max_age_days)

    manifest_candidates = [
        "release_artifacts/RELEASE_EVIDENCE_MANIFEST_2026-05-22.json",
        "RELEASE_EVIDENCE_MANIFEST_2026-05-22.json",
    ]

    with zipfile.ZipFile(zip_path, "r") as zf:
        manifest_name = next(
            (m for m in manifest_candidates if m in zf.namelist()),
            None,
        )
        if manifest_name is None:
            raise SystemExit("manifest_missing")

        try:
            manifest = json.loads(zf.read(manifest_name).decode("utf-8"))
        except Exception as exc:  # pragma: no cover - defensive parse path
            raise SystemExit(f"manifest_parse_error:{exc}") from exc

    release_name = manifest.get("release_zip") or manifest.get(
        "archive", {}
    ).get("path")
    release_sha = (
        manifest.get("release_zip_sha256")
        or manifest.get("archive_sha256")
        or manifest.get("archive", {}).get("sha256")
    )
    evidence_name = manifest.get("evidence_zip")
    evidence_sha = manifest.get("evidence_zip_sha256")

    errors: list[str] = []

    generated_at = manifest.get("generated_at_utc")
    if not isinstance(generated_at, str) or not generated_at.strip():
        errors.append("generated_at_utc missing or empty")
    else:
        raw = generated_at.strip()
        if raw.endswith("Z"):
            raw = raw[:-1] + "+00:00"
        try:
            dt = datetime.fromisoformat(raw)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            else:
                dt = dt.astimezone(timezone.utc)
            age_days = (
                datetime.now(timezone.utc) - dt
            ).total_seconds() / 86400.0
            if age_days > max_age_days_int:
                errors.append(
                    "generated_at_utc too old "
                    f"({age_days:.2f} days > {max_age_days_int} days)"
                )
        except ValueError:
            errors.append(
                f"generated_at_utc invalid ISO8601: {generated_at!r}"
            )

    status_policy = manifest.get("status_policy")
    if not isinstance(status_policy, dict):
        errors.append("status_policy missing or invalid")
    else:
        current_label = status_policy.get("current_label")
        if not isinstance(current_label, str) or not current_label.strip():
            errors.append("status_policy.current_label missing or empty")

    if release_name != exp_release_name:
        errors.append(
            f"release_name:{release_name!r}!=expected:{exp_release_name!r}"
        )
    if release_sha != exp_release_sha:
        errors.append(
            f"release_sha:{release_sha!r}!=expected:{exp_release_sha!r}"
        )

    # Older manifests may not have evidence_* fields; only enforce when present.
    if evidence_name is not None and evidence_name != exp_evidence_name:
        errors.append(
            f"evidence_name:{evidence_name!r}!=expected:{exp_evidence_name!r}"
        )
    if evidence_sha is not None and evidence_sha != exp_evidence_sha:
        errors.append(
            f"evidence_sha:{evidence_sha!r}!=expected:{exp_evidence_sha!r}"
        )

    if errors:
        raise SystemExit("manifest_mismatch:" + "; ".join(errors))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
