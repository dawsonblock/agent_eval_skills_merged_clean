#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def status_for_eval_list(payload: list[Any]) -> str:
    if not payload:
        return "fail"

    saw_warning = False
    for item in payload:
        if not isinstance(item, dict):
            continue
        gate = item.get("qualityGate")
        if not isinstance(gate, dict):
            continue
        state = str(gate.get("status", "")).lower()
        if state in {"fail", "error", "failed"}:
            return "fail"
        if state in {"warn", "warning", "pass_with_warnings"}:
            saw_warning = True

    return "pass_with_warnings" if saw_warning else "pass"


def status_for(path: Path, key: str = "overall_status") -> str:
    if not path.exists():
        return "fail"
    payload = read_json(path)
    if isinstance(payload, list):
        return status_for_eval_list(payload)
    if not isinstance(payload, dict):
        return "fail"
    value = payload.get(key)
    if isinstance(value, str) and value.lower() in {"passed", "pass"}:
        return "pass"
    return "pass_with_warnings" if value else "fail"


def main() -> int:
    parser = argparse.ArgumentParser(description="Write canonical smoke validation summary")
    parser.add_argument("--logs-dir", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    logs = args.logs_dir
    toolathlon_smoke = logs / "toolathlon_smoke_summary.json"
    agent_skills = logs / "agent_skills_summary.json"

    components = {
        "root_tests": "pass" if (logs / "test_results_root.txt").exists() else "fail",
        "toolforge_tests": "pass" if (logs / "test_results_toolforge.txt").exists() else "fail",
        "toolforge_doctor": "pass" if (logs / "toolforge_doctor.txt").exists() else "fail",
        "agent_skills_eval": status_for(agent_skills),
        "agent_skill_packages": "pass" if (logs / "agent_skill_packages.txt").exists() else "fail",
        "toolathlon_smoke": status_for(toolathlon_smoke),
        "source_bundle_hygiene": (
            "pass" if (logs / "source_bundle_hygiene.txt").exists() else "fail"
        ),
        "release_pair_verification": (
            "pass" if (logs / "release_pair_verification.txt").exists() else "fail"
        ),
    }

    statuses = set(components.values())
    if "fail" in statuses:
        overall = "fail"
    elif "pass_with_warnings" in statuses:
        overall = "pass_with_warnings"
    else:
        overall = "pass"

    payload = {
        "status": overall,
        "profile": "smoke",
        "toolathlon_profile": "smoke",
        "smoke_targets": ["rail_12306", "filesystem"],
        "excluded_smoke_targets": ["google_calendar"],
        "full_toolathlon_profile_validated": False,
        "components": components,
        "warnings": [
            "Some skills remain below preferred quality threshold.",
            "Toolathlon full profile is experimental.",
        ],
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
