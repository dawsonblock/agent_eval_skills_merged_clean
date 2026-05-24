from __future__ import annotations

from pathlib import Path

from skillforge_ai.repair_loop import RepairLoop


def run_repair(workspace_root: Path, slug: str, provider: str = "rule_based") -> dict:
    ok, attempts = RepairLoop(workspace_root=workspace_root).run(slug, provider=provider)
    return {
        "skill": slug,
        "status": "passed" if ok else "failed",
        "attempts": [a.__dict__ for a in attempts],
    }
