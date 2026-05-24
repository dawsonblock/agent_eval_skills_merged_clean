from __future__ import annotations

from pathlib import Path

from skillforge_ai.validation_runner import ValidationRunner


def run_repair(
    workspace_root: Path,
    slug: str,
    provider: str,
    max_attempts: int,
):
    runner = ValidationRunner(
        workspace_root=workspace_root,
        max_repair_attempts=max_attempts,
    )
    return runner.repair_loop(slug, provider=provider)
