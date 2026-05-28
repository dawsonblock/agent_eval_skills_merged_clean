#!/usr/bin/env python3
"""Build the final deterministic upload wrapper ZIP.

Includes source workspace + canonical release artifacts.
Excludes generated/vendor/cache directories.

Usage:
    python scripts/build_upload_wrapper.py
    python scripts/build_upload_wrapper.py --out /tmp/upload.zip
"""
from __future__ import annotations

import argparse
import hashlib
import stat
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RELEASE_ARTIFACTS = ROOT / "release_artifacts"
DEFAULT_OUT = ROOT / "release_artifacts" / "agent_eval_skills_merged_clean-upload-wrapper.zip"
REQUIRED_RELEASE_ARTIFACTS = [
    RELEASE_ARTIFACTS / "release_lock.json",
    RELEASE_ARTIFACTS / "agent_eval_skills_merged_clean-pruned-smoke.zip",
    RELEASE_ARTIFACTS / "agent_eval_skills_merged_clean-smoke-evidence-2026-05-27.zip",
    RELEASE_ARTIFACTS / "release_identity.generated.json",
]

# Top-level items included from source workspace
SOURCE_INCLUDE = [
    "ToolForge",
    "agent-skills-curated",
    "toolathlon-gym-curated",
    "scripts",
    "tests",
    "docs",
    "README.md",
    "CLAIMS_MATRIX.md",
    "SECURITY.md",
    "SECURITY_FIXTURES.md",
    "DEPLOYMENT.md",
    "WORKSPACE_HEALTH_DASHBOARD.md",
    "RELEASE_EVIDENCE_MANIFEST_2026-05-27.json",
    "RELEASE_STATUS.json",
    "RELEASE_MANIFEST.json",
    "VALIDATION_EVIDENCE.md",
    "RELEASE_ATTESTATION_2026-05-27.md",
    "release_artifacts/release_identity.generated.json",
    "release_artifacts/RELEASE_HANDOFF_2026-05-27.md",
    "release_artifacts/RELEASE_HANDOFF_2026-05-28.md",
    "setup.cfg",
    "pyrightconfig.json",
    "pytest.ini",
    "Makefile",
    "LICENSE",
    "dist/release/SHA256SUMS.txt",
]

EXCLUDE_PARTS = {
    ".git",
    ".venv",
    "venv",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "node_modules",
    ".skillforge",
    "validation_logs",
}
EXCLUDE_NAMES = {".DS_Store"}
FIXED_DATE = (2026, 5, 27, 0, 0, 0)


def should_exclude(path: Path) -> bool:
    rel = path.relative_to(ROOT)
    if rel.parts[:2] == ("release_artifacts", "validation_logs"):
        return True
    if any(part in EXCLUDE_PARTS for part in rel.parts):
        return True
    if path.name in EXCLUDE_NAMES:
        return True
    if path.suffix in {".pyc", ".pyo"}:
        return True
    return False


def iter_source_files() -> list[Path]:
    files: list[Path] = []
    for item in SOURCE_INCLUDE:
        p = ROOT / item
        if not p.exists():
            continue
        if p.is_file():
            if not should_exclude(p):
                files.append(p)
        else:
            for child in p.rglob("*"):
                if child.is_file() and not should_exclude(child):
                    files.append(child)
    return sorted(files, key=lambda p: p.relative_to(ROOT).as_posix())


def iter_release_artifact_files() -> list[Path]:
    return sorted(REQUIRED_RELEASE_ARTIFACTS, key=lambda p: p.name)


def verify_required_release_artifacts() -> None:
    missing = [str(p) for p in REQUIRED_RELEASE_ARTIFACTS if not p.exists()]
    if missing:
        raise SystemExit(
            "FAIL: missing required release artifact(s):\n" + "\n".join(missing)
        )


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build the final upload wrapper ZIP.")
    parser.add_argument(
        "--out",
        type=Path,
        default=DEFAULT_OUT,
        help="Output path for the wrapper ZIP",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    verify_required_release_artifacts()

    out_path: Path = args.out
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if out_path.exists():
        out_path.unlink()

    source_files = iter_source_files()
    artifact_files = iter_release_artifact_files()

    # Exclude the wrapper itself from artifact list to avoid including old wrapper in new
    artifact_files = [f for f in artifact_files if f != out_path and "upload-wrapper" not in f.name]

    with zipfile.ZipFile(out_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        written_paths: set[str] = set()
        for path in source_files:
            rel = path.relative_to(ROOT).as_posix()
            if rel in written_paths:
                continue
            info = zipfile.ZipInfo(rel, FIXED_DATE)
            info.external_attr = (stat.S_IFREG | 0o644) << 16
            zf.writestr(info, path.read_bytes())
            written_paths.add(rel)

        for path in artifact_files:
            rel = path.relative_to(ROOT).as_posix()
            if rel in written_paths:
                continue
            info = zipfile.ZipInfo(rel, FIXED_DATE)
            info.external_attr = (stat.S_IFREG | 0o644) << 16
            zf.writestr(info, path.read_bytes())
            written_paths.add(rel)

    digest = sha256(out_path)
    size_mb = out_path.stat().st_size / (1024 * 1024)
    print(f"Wrote {out_path}")
    print(f"Size:   {size_mb:.1f} MB")
    print(f"SHA256: {digest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
