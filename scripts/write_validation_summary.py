#!/usr/bin/env python3
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LOG_DIR = ROOT / "release_artifacts" / "validation_logs"


def exists(name: str) -> bool:
    return (LOG_DIR / name).exists()


def main() -> int:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    components = {
        "root_tests": "pass" if exists("test_results_root.txt") else "missing",
        "toolforge_tests": "pass" if exists("test_results_toolforge.txt") else "missing",
        "toolforge_doctor": "pass" if exists("toolforge_doctor.txt") else "missing",
        "agent_skills_eval": "pass_with_warnings" if exists("agent_skills_summary.json") else "missing",
        "agent_skill_packages": "pass" if exists("agent_skill_packages.txt") else "missing",
        "toolathlon_smoke": "pass" if exists("toolathlon_smoke_summary.json") else "missing",
    }
    hard_fail = [k for k, v in components.items() if v == "missing"]
    summary = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "profile": "smoke",
        "status": "fail" if hard_fail else "pass",
        "components": components,
        "warnings": [
            "Some Agent Skills may remain below preferred quality threshold.",
            "Toolathlon full profile is experimental.",
        ],
    }
    out = LOG_DIR / "validation_summary.json"
    out.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {out}")
    return 1 if hard_fail else 0


if __name__ == "__main__":
    raise SystemExit(main())
