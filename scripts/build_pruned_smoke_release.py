#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import os
from pathlib import Path
import stat
import zipfile


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = REPO_ROOT / "release_artifacts" / "agent_eval_skills_merged_clean-pruned-smoke.zip"

INCLUDE_TOP = {
    "ToolForge",
    "agent-skills-curated",
    "toolathlon-gym-curated",
    "scripts",
    "tests",
    "README.md",
    "RELEASE_STATUS.json",
    "RELEASE_MANIFEST.json",
    "VALIDATION_EVIDENCE.md",
    "RELEASE_ATTESTATION_2026-05-27.md",
}

EXCLUDE_DIR_NAMES = {
    ".git",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "node_modules",
    "dist",
    "build",
    ".venv",
    "venv",
    ".skillforge",
    "withdrawn",
}

EXCLUDE_SUFFIXES = {".pyc", ".pyo", ".log", ".tmp"}
EXCLUDE_PARTS = {
    ".DS_Store",
    "__MACOSX",
}

FIXED_DT = (2026, 5, 27, 0, 0, 0)


def is_excluded(rel_path: Path) -> bool:
    parts = set(rel_path.parts)
    if parts & EXCLUDE_PARTS:
        return True
    if parts & EXCLUDE_DIR_NAMES:
        return True
    name = rel_path.name
    if any(name.endswith(sfx) for sfx in EXCLUDE_SUFFIXES):
        return True
    return False


def collect_files() -> list[Path]:
    files: list[Path] = []
    for top in sorted(INCLUDE_TOP):
        p = REPO_ROOT / top
        if not p.exists():
            continue
        if p.is_file():
            rel = p.relative_to(REPO_ROOT)
            if not is_excluded(rel):
                files.append(rel)
            continue

        for path in sorted(p.rglob("*")):
            if not path.is_file():
                continue
            rel = path.relative_to(REPO_ROOT)
            if is_excluded(rel):
                continue
            files.append(rel)
    return files


def normalized_mode(path: Path) -> int:
    st = path.stat()
    mode = stat.S_IMODE(st.st_mode)
    if mode & stat.S_IXUSR:
        return 0o755
    return 0o644


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def build_zip(out_path: Path) -> str:
    files = collect_files()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if out_path.exists():
        out_path.unlink()

    with zipfile.ZipFile(out_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for rel in files:
            src = REPO_ROOT / rel
            zi = zipfile.ZipInfo(str(rel).replace(os.sep, "/"), FIXED_DT)
            zi.external_attr = normalized_mode(src) << 16
            zi.compress_type = zipfile.ZIP_DEFLATED
            data = src.read_bytes()
            zf.writestr(zi, data)

    return sha256_of(out_path)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build deterministic pruned smoke release ZIP.")
    parser.add_argument("--profile", default="smoke", choices=["smoke"], help="Validation profile")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT, help="Output ZIP path")
    args = parser.parse_args()

    digest = build_zip(args.out)
    print(f"Wrote {args.out}")
    print(f"SHA256: {digest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
