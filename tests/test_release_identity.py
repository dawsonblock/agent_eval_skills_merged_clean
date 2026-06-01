from __future__ import annotations

import hashlib
import json
import os
import subprocess
import tempfile
import zipfile
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
LOCK_PATH = REPO_ROOT / "release_artifacts" / "release_lock.json"


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _artifact_paths() -> tuple[Path, Path, dict]:
    lock = _load_json(LOCK_PATH)
    release_zip = REPO_ROOT / "release_artifacts" / lock["release_zip"]
    evidence_zip = REPO_ROOT / "release_artifacts" / lock["evidence_zip"]
    return release_zip, evidence_zip, lock


def test_release_lock_exists() -> None:
    assert LOCK_PATH.exists(), "release_lock.json must exist"


def test_release_and_evidence_archives_exist() -> None:
    release_zip, evidence_zip, _ = _artifact_paths()
    assert release_zip.exists(), f"Missing release zip: {release_zip}"
    assert evidence_zip.exists(), f"Missing evidence zip: {evidence_zip}"


def test_hashes_match_release_lock() -> None:
    release_zip, evidence_zip, lock = _artifact_paths()
    assert _sha256(release_zip) == lock["release_sha256"]
    assert _sha256(evidence_zip) == lock["evidence_sha256"]


def test_release_zip_hygiene_passes() -> None:
    release_zip, _, _ = _artifact_paths()
    result = subprocess.run(
        [
            "python",
            "scripts/check_source_bundle_hygiene.py",
            str(release_zip),
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + "\n" + result.stderr


def test_evidence_contains_validation_summary() -> None:
    _, evidence_zip, _ = _artifact_paths()
    with zipfile.ZipFile(evidence_zip) as zf:
        assert ".validation_logs/validation_summary.json" in set(zf.namelist())


def test_verify_release_pair_passes() -> None:
    result = subprocess.run(
        ["python", "scripts/verify_release_pair.py"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + "\n" + result.stderr


def test_verify_release_pair_wrapper_passes_with_defaults_and_env_paths() -> None:
    release_zip, evidence_zip, _ = _artifact_paths()
    default_result = subprocess.run(
        ["bash", "scripts/verify_release_pair.sh"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert default_result.returncode == 0, default_result.stdout + "\n" + default_result.stderr

    env_result = subprocess.run(
        ["bash", "scripts/verify_release_pair.sh"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
        env={
            **os.environ,
            "RELEASE_ZIP_PATH": str(release_zip.relative_to(REPO_ROOT)),
            "EVIDENCE_ZIP_PATH": str(evidence_zip.relative_to(REPO_ROOT)),
        },
    )
    assert env_result.returncode == 0, env_result.stdout + "\n" + env_result.stderr


def test_release_pair_call_sites_do_not_pass_unsupported_strict_flag() -> None:
    call_site_paths = [
        REPO_ROOT / ".github" / "workflows" / "smoke-release.yml",
        REPO_ROOT / "docs" / "CLEAN_CHECKOUT_VALIDATION.md",
    ]

    for path in call_site_paths:
        lines = path.read_text(encoding="utf-8").splitlines()
        for index, line in enumerate(lines):
            if "verify_release_pair.py" not in line:
                continue
            command_window = "\n".join(lines[index : index + 4])
            assert "--strict" not in command_window, (
                f"{path.relative_to(REPO_ROOT)} passes unsupported --strict "
                "to scripts/verify_release_pair.py"
            )


def test_classifier_missing_path_returns_clean_json_failure() -> None:
    with tempfile.TemporaryDirectory() as td:
        verdict = Path(td) / "missing.json"
        missing = REPO_ROOT / "release_artifacts" / "does-not-exist.zip"
        result = subprocess.run(
            [
                "python",
                "scripts/classify_release_artifact.py",
                str(missing),
                "--json-out",
                str(verdict),
            ],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode != 0
        payload = _load_json(verdict)
        assert payload == {
            "status": "fail",
            "verdict": "missing_artifact",
            "canonical": False,
            "path": str(missing),
            "reasons": ["artifact path does not exist"],
        }


def test_classifier_wrapper_bundle_returns_unbound_verdict() -> None:
    release_zip, evidence_zip, _ = _artifact_paths()
    with tempfile.TemporaryDirectory() as td:
        wrapper = Path(td) / "wrapper.zip"
        wrapper.write_bytes(b"wrapper-source-bundle")
        verdict = Path(td) / "wrapper_verdict.json"
        result = subprocess.run(
            [
                "python",
                "scripts/classify_release_artifact.py",
                str(wrapper),
                "--evidence",
                str(evidence_zip),
                "--json-out",
                str(verdict),
            ],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0
        payload = _load_json(verdict)
        assert payload["status"] == "pass"
        assert payload["verdict"] == "unbound_wrapper_source_bundle"
        assert payload["canonical"] is False
        assert payload["archive"]["path"] == str(wrapper)
        assert release_zip.name != wrapper.name


def test_classifier_canonical_bundle_returns_canonical_verdict() -> None:
    release_zip, evidence_zip, _ = _artifact_paths()
    with tempfile.TemporaryDirectory() as td:
        verdict = Path(td) / "canonical_verdict.json"
        result = subprocess.run(
            [
                "python",
                "scripts/classify_release_artifact.py",
                str(release_zip),
                "--evidence",
                str(evidence_zip),
                "--json-out",
                str(verdict),
            ],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0
        payload = _load_json(verdict)
        assert payload["status"] == "pass"
        assert payload["verdict"] == "canonical_smoke_release"
        assert payload["canonical"] is True
