"""Helpers for subprocess-based ToolForge CLI end-to-end tests."""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Sequence


_ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")


def find_toolforge_root() -> Path:
    """Locate the ToolForge root directory by looking for pyproject.toml and packages/."""
    here = Path(__file__).resolve()
    for parent in [here, *here.parents]:
        if (parent / "pyproject.toml").exists() and (parent / "packages").exists():
            return parent
    raise RuntimeError("Could not locate ToolForge root")


def build_toolforge_command(env: dict[str, str]) -> tuple[list[str], Path | None, dict[str, str]]:
    """Build the toolforge command and cleaned environment for subprocess execution."""
    root = find_toolforge_root()
    use_module = env.get("TOOLFORGE_TEST_USE_MODULE_CLI") == "1"
    
    cleaned_env = env.copy()
    for key in (
        "PYTEST_CURRENT_TEST",
        "PYTEST_VERSION",
        "PYTEST_ADDOPTS",
        "PYTEST_PLUGINS",
    ):
        cleaned_env.pop(key, None)
    cleaned_env["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
    cleaned_env["PYTHONDONTWRITEBYTECODE"] = "1"
    cleaned_env["PYTHONUNBUFFERED"] = "1"
    
    existing_pythonpath = cleaned_env.get("PYTHONPATH", "")
    paths = [str(root), str(root / "apps" / "cli")]
    if existing_pythonpath:
        paths.append(existing_pythonpath)
    cleaned_env["PYTHONPATH"] = os.pathsep.join(paths)
    
    if use_module:
        return [sys.executable, "-m", "apps.cli.toolforge_cli.main"], root, cleaned_env
    
    cli_path = shutil.which("toolforge")
    if cli_path:
        return [cli_path], None, cleaned_env
    
    # Fallback should be deterministic, not implicit-PYTHONPATH-dependent
    return [sys.executable, "-m", "apps.cli.toolforge_cli.main"], root, cleaned_env


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
    
    cmd_prefix, _, cleaned_env = build_toolforge_command(effective_env)
    
    result = subprocess.run(
        [*cmd_prefix, *args],
        cwd=str(cwd),
        text=True,
        capture_output=True,
        timeout=timeout,
        env=cleaned_env,
        check=False,
    )
    return result


def combined_output(result: subprocess.CompletedProcess[str]) -> str:
    stderr = "\n" + result.stderr if result.stderr else ""
    return (result.stdout or "") + stderr


def strip_ansi(text: str) -> str:
    return _ANSI_RE.sub("", text)
