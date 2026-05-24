from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from skillforge_ai.mcp_controller import MCPController


def smoke_skill_server(server_path: Path) -> bool:
    ctrl = MCPController()
    return ctrl.smoke_test(server_path)


def smoke_toolathlon_profile(
    workspace_root: Path,
    profile: str,
) -> tuple[int, str, str, Path]:
    repo_root = workspace_root
    toolathlon_root = repo_root / "toolathlon-gym-curated"
    if not toolathlon_root.exists():
        parent_candidate = repo_root.parent / "toolathlon-gym-curated"
        if parent_candidate.exists():
            repo_root = repo_root.parent
            toolathlon_root = parent_candidate

    smoke_script = toolathlon_root / "scripts" / "smoke_mcp_servers.py"
    if not smoke_script.exists():
        raise FileNotFoundError(f"Toolathlon smoke script not found: {smoke_script}")

    summary_path = repo_root / ".validation_logs" / "toolathlon_mcp_smoke_summary.json"
    summary_path.parent.mkdir(parents=True, exist_ok=True)

    completed = subprocess.run(
        [
            sys.executable,
            str(smoke_script),
            "--profile",
            profile,
            "--json-output",
            str(summary_path),
        ],
        cwd=str(toolathlon_root),
        capture_output=True,
        text=True,
        check=False,
    )
    return completed.returncode, completed.stdout, completed.stderr, summary_path
