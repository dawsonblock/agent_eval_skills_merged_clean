#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import stat
from pathlib import Path
import zipfile


ROOT = Path(__file__).resolve().parents[1]
LOG_DIR = ROOT / "release_artifacts" / "validation_logs"
OUT = ROOT / "release_artifacts" / "agent_eval_skills_merged_clean-smoke-evidence-2026-05-27.zip"
FIXED_DATE = (2026, 5, 27, 0, 0, 0)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    if not LOG_DIR.exists():
        print(f"FAIL: missing validation logs: {LOG_DIR}")
        return 1

    OUT.parent.mkdir(parents=True, exist_ok=True)
    if OUT.exists():
        OUT.unlink()

    files = sorted([p for p in LOG_DIR.rglob("*") if p.is_file()], key=lambda p: p.relative_to(LOG_DIR).as_posix())
    with zipfile.ZipFile(OUT, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for path in files:
            rel = Path(".validation_logs") / path.relative_to(LOG_DIR)
            info = zipfile.ZipInfo(rel.as_posix(), FIXED_DATE)
            info.external_attr = (stat.S_IFREG | 0o644) << 16
            zf.writestr(info, path.read_bytes())

    digest = sha256(OUT)
    print(f"Wrote {OUT}")
    print(f"SHA256: {digest}")

    lock_path = ROOT / "release_artifacts" / "release_lock.json"
    if lock_path.exists():
        lock = json.loads(lock_path.read_text(encoding="utf-8"))
        lock["evidence_sha256"] = digest
        lock_path.write_text(json.dumps(lock, indent=2) + "\n", encoding="utf-8")
        print(f"Updated {lock_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
