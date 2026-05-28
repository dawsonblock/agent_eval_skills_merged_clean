#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import stat
from datetime import datetime, timezone
from pathlib import Path
import zipfile


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LOG_DIR = ROOT / "release_artifacts" / "validation_logs"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def parse_fixed_date(date_str: str | None) -> tuple[int, int, int, int, int, int]:
    if date_str:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
    else:
        dt = datetime.now(timezone.utc)
    return (dt.year, dt.month, dt.day, 0, 0, 0)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build smoke evidence zip from validation logs")
    parser.add_argument("--logs", type=Path, default=DEFAULT_LOG_DIR)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--release-sha")
    parser.add_argument("--date", help="Override zip entry date as YYYY-MM-DD")
    args = parser.parse_args()

    log_dir = args.logs
    if args.out:
        out = args.out
    else:
        stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        out = (
            ROOT
            / "release_artifacts"
            / f"agent_eval_skills_merged_clean-smoke-evidence-{stamp}.zip"
        )
    fixed_date = parse_fixed_date(args.date)

    if not log_dir.exists():
        print(f"FAIL: missing validation logs: {log_dir}")
        return 1

    lock_path = ROOT / "release_artifacts" / "release_lock.json"
    lock: dict[str, object] = {}
    if lock_path.exists():
        lock = json.loads(lock_path.read_text(encoding="utf-8"))
        lock_release_sha = str(lock.get("release_sha256", ""))
        if args.release_sha and lock_release_sha and args.release_sha != lock_release_sha:
            print("FAIL: release_sha does not match lock release_sha256")
            print(f"lock: {lock_release_sha}")
            print(f"arg:  {args.release_sha}")
            return 1

        release_hashes = {
            "release_zip": lock.get("release_zip", ""),
            "release_sha256": args.release_sha or lock.get("release_sha256", ""),
            "evidence_zip": out.name,
            "profile": lock.get("validation_profile", "smoke"),
        }
        (log_dir / "release_hashes.json").write_text(
            json.dumps(release_hashes, indent=2) + "\n", encoding="utf-8"
        )

    out.parent.mkdir(parents=True, exist_ok=True)
    if out.exists():
        out.unlink()

    files = sorted(
        [p for p in log_dir.rglob("*") if p.is_file()],
        key=lambda p: p.relative_to(log_dir).as_posix(),
    )
    with zipfile.ZipFile(out, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for path in files:
            rel = Path(".validation_logs") / path.relative_to(log_dir)
            info = zipfile.ZipInfo(rel.as_posix(), fixed_date)
            info.external_attr = (stat.S_IFREG | 0o644) << 16
            zf.writestr(info, path.read_bytes())

    digest = sha256(out)
    print(f"Wrote {out}")
    print(f"SHA256: {digest}")

    if lock_path.exists():
        lock["evidence_zip"] = out.name
        lock["evidence_sha256"] = digest
        lock_path.write_text(json.dumps(lock, indent=2) + "\n", encoding="utf-8")
        print(f"Updated {lock_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
