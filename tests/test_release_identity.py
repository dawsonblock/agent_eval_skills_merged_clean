from __future__ import annotations

import hashlib
import json
import subprocess
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


REQUIRED_LOGS = [
    ".validation_logs/validation_summary.json",
    ".validation_logs/toolforge_validator_tests.log",
    ".validation_logs/toolforge_registry_tests.log",
    ".validation_logs/agent_skills_eval.json",
    ".validation_logs/toolathlon_smoke_preflight.json",
]


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def test_release_status_schema_and_values() -> None:
    status_path = REPO_ROOT / "RELEASE_STATUS.json"
    assert status_path.exists(), "RELEASE_STATUS.json must exist"

    payload = _load_json(status_path)
    allowed = {
        "SOURCE_BUNDLE",
        "CANONICAL_SMOKE_RELEASE",
        "CANONICAL_FULL_RELEASE",
        "WITHDRAWN_RELEASE",
    }
    assert payload["release_classification"] in allowed
    assert payload["toolathlon_profile"] == "smoke"
    assert payload["smoke_targets"] == ["rail_12306", "filesystem"]
    assert payload["removed_smoke_targets"] == ["google_calendar"]
    assert "google_calendar" not in payload["smoke_targets"]
    assert payload["production_claim_allowed"] is False


def test_release_and_evidence_archives_exist() -> None:
    assert (REPO_ROOT / "agent_eval_skills_merged_clean-pruned-smoke.zip").exists()
    assert (REPO_ROOT / "agent_eval_skills_merged_clean-smoke-evidence-2026-05-22.zip").exists()


def test_validation_logs_present_and_recent() -> None:
    now = datetime.now(timezone.utc)
    max_age = timedelta(days=14)

    for rel in REQUIRED_LOGS:
        path = REPO_ROOT / rel
        assert path.exists(), f"Missing required validation log: {rel}"
        mtime = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
        assert now - mtime <= max_age, f"Validation log is stale: {rel}"


def test_validation_summary_tracks_two_target_smoke_profile() -> None:
    summary = _load_json(REPO_ROOT / ".validation_logs" / "validation_summary.json")

    assert summary["toolathlon_profile"] == "smoke"
    assert summary["smoke_targets"] == ["rail_12306", "filesystem"]
    assert summary["excluded_smoke_targets"] == ["google_calendar"]
    assert summary["full_toolathlon_profile_validated"] is False
    assert "google_calendar" not in summary["smoke_targets"]


def test_verify_release_pair_succeeds_for_source_bundle_mode() -> None:
    result = subprocess.run(
        ["bash", "scripts/verify_release_pair.sh"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + "\n" + result.stderr
    assert "Classification: Source bundle" in result.stdout


def test_release_manifest_contains_current_status_hash() -> None:
    manifest_path = REPO_ROOT / "RELEASE_MANIFEST.json"
    manifest = _load_json(manifest_path)
    files = manifest.get("files", [])

    status_sha = _sha256(REPO_ROOT / "RELEASE_STATUS.json")
    status_entries = [item for item in files if item.get("path") == "RELEASE_STATUS.json"]

    assert status_entries, "RELEASE_MANIFEST must include RELEASE_STATUS.json"
    assert status_entries[0]["sha256"] == status_sha


def test_classification_reports_non_canonical_in_source_bundle_mode() -> None:
    release_zip = REPO_ROOT / "agent_eval_skills_merged_clean-pruned-smoke.zip"
    evidence_zip = REPO_ROOT / "agent_eval_skills_merged_clean-smoke-evidence-2026-05-22.zip"

    with tempfile.TemporaryDirectory() as td:
        verdict = Path(td) / "verdict.json"
        result = subprocess.run(
            [
                "bash",
                "scripts/classify_release_upload.sh",
                "--release",
                str(release_zip),
                "--evidence",
                str(evidence_zip),
                "--json-output",
                str(verdict),
            ],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 1
        assert verdict.exists(), "classifier did not produce verdict JSON"
        payload = _load_json(verdict)
        assert payload["classification"] == "clean_new_candidate"
        reasons = "\n".join(payload.get("reasons", []))
        assert "SOURCE_BUNDLE" in reasons


def test_withdrawn_evidence_is_quarantined_from_release_artifacts_root() -> None:
    root_entries = list((REPO_ROOT / "release_artifacts").glob("*2026-05-23*.zip"))
    assert not root_entries, "Withdrawn evidence ZIPs must not sit in release_artifacts root"

    withdrawn_readme = REPO_ROOT / "release_artifacts" / "withdrawn" / "README.md"
    assert withdrawn_readme.exists(), "release_artifacts/withdrawn/README.md must exist"
