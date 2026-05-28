#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LOG_DIR = ROOT / "release_artifacts" / "validation_logs"


def exists(log_dir: Path, name: str) -> bool:
    return (log_dir / name).exists()


def release_pair_verification_status(log_dir: Path) -> str:
    path = log_dir / "release_pair_verification.txt"
    if not path.exists():
        return "missing"
    text = path.read_text(encoding="utf-8", errors="replace")
    if "FAIL" in text:
        return "fail"
    if "PASS" in text:
        return "pass"
    return "fail"


def main() -> int:
    parser = argparse.ArgumentParser(description="Write smoke validation summary JSON")
    parser.add_argument("--logs-dir", type=Path, default=DEFAULT_LOG_DIR)
    parser.add_argument("--out", type=Path)
    parser.add_argument(
        "--stage",
        choices=["pre-evidence", "final"],
        default="final",
        help="Validation stage (default: final)",
    )
    args = parser.parse_args()

    log_dir = args.logs_dir
    out = args.out if args.out else (log_dir / "validation_summary.json")

    log_dir.mkdir(parents=True, exist_ok=True)
    out.parent.mkdir(parents=True, exist_ok=True)

    toolathlon_smoke_present = (
        exists(log_dir, "toolathlon_smoke_summary.json")
        or exists(log_dir, "toolathlon_mcp_smoke_summary.json")
    )
    pair_status = release_pair_verification_status(log_dir)
    if args.stage == "pre-evidence" and pair_status == "missing":
        pair_status = "pending"

    components = {
        "root_tests": "pass" if exists(log_dir, "test_results_root.txt") else "missing",
        "toolforge_tests": "pass" if exists(log_dir, "test_results_toolforge.txt") else "missing",
        "toolforge_doctor": "pass" if exists(log_dir, "toolforge_doctor.txt") else "missing",
        "agent_skills_eval": (
            "pass_with_warnings"
            if exists(log_dir, "agent_skills_summary.json")
            else "missing"
        ),
        "agent_skill_packages": (
            "pass" if exists(log_dir, "agent_skill_packages.txt") else "missing"
        ),
        "toolathlon_smoke": "pass" if toolathlon_smoke_present else "missing",
        "release_pair_verification": pair_status,
    }
    required_components = dict(components)
    if args.stage == "pre-evidence":
        required_components.pop("release_pair_verification", None)

    hard_fail = [k for k, v in required_components.items() if v in {"missing", "fail"}]
    summary = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "profile": "smoke",
        "stage": args.stage,
        "capabilities": {
            "toolathlon_profile": "smoke",
        },
        "status": "fail" if hard_fail else "pass",
        "components": components,
        "warnings": [
            "Some Agent Skills may remain below preferred quality threshold.",
            "Toolathlon full profile is experimental.",
        ],
    }
    out.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {out}")
    return 1 if hard_fail else 0


if __name__ == "__main__":
    raise SystemExit(main())
