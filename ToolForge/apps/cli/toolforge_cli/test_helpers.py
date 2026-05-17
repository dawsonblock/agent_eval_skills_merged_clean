"""Helpers for subprocess-based ToolForge CLI end-to-end tests."""
from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Sequence


_ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")


def _resolve_toolforge_command() -> tuple[list[str], Path | None]:
    # During tests, always use module execution with explicit PYTHONPATH
    # to avoid subprocess hangs that occur with installed console scripts under pytest
    toolforge_root = Path(__file__).parent.parent.parent.parent
    return [sys.executable, "-m", "apps.cli.toolforge_cli.main"], toolforge_root


def run_toolforge(
    args: Sequence[str],
    *,
    cwd: Path,
    timeout: float = 120.0,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    effective_env = os.environ.copy()
    if env:
        effective_env.update(env)
    effective_env.setdefault("PYTHONUNBUFFERED", "1")

    # Strip pytest environment variables to prevent subprocess hangs
    for key in (
        "PYTEST_CURRENT_TEST",
        "PYTEST_VERSION",
        "PYTEST_ADDOPTS",
        "PYTEST_PLUGINS",
    ):
        effective_env.pop(key, None)
    effective_env["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
    effective_env["PYTHONDONTWRITEBYTECODE"] = "1"

    cmd, toolforge_root = _resolve_toolforge_command()
    if toolforge_root:
        # Add PYTHONPATH to ensure ToolForge packages can be imported
        effective_env["PYTHONPATH"] = str(toolforge_root)

    return subprocess.run(
        [*cmd, *args],
        cwd=str(cwd),
        text=True,
        capture_output=True,
        timeout=timeout,
        env=effective_env,
        check=False,
    )


def combined_output(result: subprocess.CompletedProcess[str]) -> str:
    stderr = "\n" + result.stderr if result.stderr else ""
    return (result.stdout or "") + stderr


def strip_ansi(text: str) -> str:
    return _ANSI_RE.sub("", text)
