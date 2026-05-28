#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import stat
import zipfile


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "release_artifacts" / "agent_eval_skills_merged_clean-pruned-smoke.zip"

INCLUDE = [
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
    "dist",
    "build",
    ".skillforge",
}
EXCLUDE_NAMES = {
    ".DS_Store",
}
FIXED_DATE = (2026, 5, 27, 0, 0, 0)


def should_exclude(path: Path) -> bool:
    rel = path.relative_to(ROOT)
    if any(part in EXCLUDE_PARTS for part in rel.parts):
        return True
    if path.name in EXCLUDE_NAMES:
        return True
    if path.suffix in {".pyc", ".pyo"}:
        return True
    return False


def iter_files() -> list[Path]:
    files = []
    for item in INCLUDE:
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


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build the pruned smoke release ZIP."
    )
    parser.add_argument(
        "--profile",
        default="smoke",
        choices=["smoke", "full"],
        help="Validation profile (default: smoke)",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=OUT,
        help="Output path for the release ZIP (default: release_artifacts/...pruned-smoke.zip)",
    )
    parser.add_argument(
        "--update-lock",
        action="store_true",
        default=False,
        help="Update release_lock.json release_sha256 after building (default: off)",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    out_path = args.out
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if out_path.exists():
        out_path.unlink()
    with zipfile.ZipFile(out_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for path in iter_files():
            rel = path.relative_to(ROOT).as_posix()
            info = zipfile.ZipInfo(rel, FIXED_DATE)
            info.external_attr = (stat.S_IFREG | 0o644) << 16
            zf.writestr(info, path.read_bytes())
    digest = sha256(out_path)
    print(f"Wrote {out_path}")
    print(f"SHA256: {digest}")

    if args.update_lock:
        lock_path = ROOT / "release_artifacts" / "release_lock.json"
        if lock_path.exists():
            lock = json.loads(lock_path.read_text(encoding="utf-8"))
            lock["release_sha256"] = digest
            lock_path.write_text(json.dumps(lock, indent=2) + "\n", encoding="utf-8")
            print(f"Updated {lock_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
