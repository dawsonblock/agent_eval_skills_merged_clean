"""
Sandbox runner — executes commands at the configured isolation level.

Sandbox levels:
  0 — direct subprocess, no isolation
  1 — env isolation (minimal PATH, secrets stripped)
  2 — subprocess with timeout + env isolation (DEFAULT)
  3 — Docker container with resource limits
  4 — Docker container with read-only filesystem + seccomp
"""
from __future__ import annotations

import os
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path

from packages.core.process_timeout import ProcessTimeoutError, run_with_process_tree_timeout


_SAFE_ENV_KEYS = frozenset({
    "PATH", "HOME", "TMPDIR", "TEMP", "TMP",
    "LANG", "LC_ALL", "LC_CTYPE",
    "PYTHONDONTWRITEBYTECODE", "PYTHONUNBUFFERED",
    "VIRTUAL_ENV", "CONDA_PREFIX",
})

_SECRET_SUFFIXES = (
    "_KEY", "_SECRET", "_TOKEN", "_PASSWORD", "_PASS",
    "_CREDENTIAL", "_CREDENTIALS", "_API_KEY", "_AUTH",
)

_DEFAULT_DOCKER_IMAGE = "python:3.12-slim"
_DOCKER_CPU_LIMIT = "1"
_DOCKER_MEM_LIMIT = "512m"


def _to_text(value: bytes | str | None) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return value


@dataclass
class SandboxResult:
    stdout: str
    stderr: str
    exit_code: int
    timed_out: bool
    wall_time_ms: float

    @property
    def success(self) -> bool:
        return self.exit_code == 0 and not self.timed_out


def _strip_secrets(env: dict[str, str]) -> dict[str, str]:
    """Return a copy of *env* with likely-secret keys removed."""
    return {
        k: v for k, v in env.items()
        if not any(k.upper().endswith(s) for s in _SECRET_SUFFIXES)
    }


def _minimal_env(extra: dict[str, str] | None = None) -> dict[str, str]:
    """Build a minimal env dict from the current process environment."""
    base = {k: v for k, v in os.environ.items() if k in _SAFE_ENV_KEYS}
    base = _strip_secrets(base)
    if extra:
        base.update(_strip_secrets(extra))
    return base


def run_in_sandbox(
    cmd: list[str],
    sandbox_level: int = 2,
    timeout_s: float = 30.0,
    env: dict[str, str] | None = None,
    cwd: str | None = None,
    docker_image: str = _DEFAULT_DOCKER_IMAGE,
) -> SandboxResult:
    """
    Execute *cmd* at the given *sandbox_level* and return a SandboxResult.
    """
    start = time.monotonic()

    if sandbox_level >= 3:
        return _run_docker(
            cmd, sandbox_level, timeout_s, env, cwd, docker_image, start
        )

    # Levels 0-2
    run_env: dict[str, str] | None
    if sandbox_level == 0:
        run_env = dict(os.environ) if env is None else {**os.environ, **env}
    else:
        run_env = _minimal_env(env)

    # Use process-tree timeout for sandbox level 2+ to prevent hanging child processes
    if sandbox_level >= 2:
        try:
            result = run_with_process_tree_timeout(
                cmd,
                Path(cwd) if cwd else Path.cwd(),
                run_env,
                timeout=timeout_s,
            )
            wall_ms = (time.monotonic() - start) * 1000
            return SandboxResult(
                stdout=result.stdout,
                stderr=result.stderr,
                exit_code=result.returncode,
                timed_out=False,
                wall_time_ms=wall_ms,
            )
        except ProcessTimeoutError as exc:
            # Timeout occurred - process-tree timeout already killed the process group
            wall_ms = (time.monotonic() - start) * 1000
            return SandboxResult(
                stdout="",
                stderr=str(exc),
                exit_code=-1,
                timed_out=True,
                wall_time_ms=wall_ms,
            )
    else:
        # Level 0-1: no sandboxing guarantees, but still use process-tree timeout
        # handling so timeouts cannot hang on inherited child-process pipes.
        try:
            result = run_with_process_tree_timeout(
                cmd,
                Path(cwd) if cwd else Path.cwd(),
                run_env or dict(os.environ),
                timeout=timeout_s,
            )
            wall_ms = (time.monotonic() - start) * 1000
            return SandboxResult(
                stdout=result.stdout,
                stderr=result.stderr,
                exit_code=result.returncode,
                timed_out=False,
                wall_time_ms=wall_ms,
            )
        except ProcessTimeoutError as exc:
            wall_ms = (time.monotonic() - start) * 1000
            return SandboxResult(
                stdout="",
                stderr=str(exc),
                exit_code=-1,
                timed_out=True,
                wall_time_ms=wall_ms,
            )


def _run_docker(
    cmd: list[str],
    sandbox_level: int,
    timeout_s: float,
    env: dict[str, str] | None,
    cwd: str | None,
    image: str,
    start: float,
) -> SandboxResult:
    """
    Run a command inside a Docker container.
    Maps host paths to container mount points and replaces absolute interpreters.
    """
    # Normalize cmd paths: replace host Python paths and tool paths
    # Ensure cwd comparison uses a separator boundary so that a cwd of
    # '/tmp/tools/csv-cleaner' does not incorrectly match
    # '/tmp/tools/csv-cleaner-v2/tool.py'.
    cwd_prefix = (cwd.rstrip("/") + "/") if cwd else ""
    norm_cmd: list[str] = []
    for arg in cmd:
        if arg.startswith("/") and arg.endswith(".py"):
            # Tool script: if in cwd, map to /workspace
            if cwd_prefix and arg.startswith(cwd_prefix):
                rel_path = arg[len(cwd_prefix):]
                norm_cmd.append(f"/workspace/{rel_path}")
            else:
                norm_cmd.append(arg)
        elif arg.startswith("/usr/local/bin/python") or arg.startswith("/usr/bin/python"):
            # Python interpreter: normalize to /usr/bin/python3 in container
            norm_cmd.append("/usr/bin/python3")
        elif arg.startswith("/") and cwd_prefix and arg.startswith(cwd_prefix):
            # Any path within cwd: map to /workspace
            rel_path = arg[len(cwd_prefix):]
            norm_cmd.append(f"/workspace/{rel_path}")
        else:
            norm_cmd.append(arg)

    docker_cmd = [
        "docker", "run",
        "--rm",
        "--network=none",
        f"--cpus={_DOCKER_CPU_LIMIT}",
        f"--memory={_DOCKER_MEM_LIMIT}",
        "--cap-drop=ALL",
        "--security-opt=no-new-privileges",
        "--pids-limit=128",
        "--user=65534:65534",
        "--read-only",
        "--tmpfs=/tmp:rw,noexec,nosuid,size=64m",
    ]

    if cwd:
        docker_cmd += ["-v", f"{cwd}:/workspace:ro", "-w", "/workspace"]

    # Pass env vars explicitly (secrets already stripped)
    safe_env = _minimal_env(env)
    for k, v in safe_env.items():
        docker_cmd += ["-e", f"{k}={v}"]

    docker_cmd.append(image)
    docker_cmd.extend(norm_cmd)

    try:
        proc = subprocess.run(
            docker_cmd,
            capture_output=True,
            text=True,
            timeout=timeout_s,
        )
        wall_ms = (time.monotonic() - start) * 1000
        return SandboxResult(
            stdout=proc.stdout,
            stderr=proc.stderr,
            exit_code=proc.returncode,
            timed_out=False,
            wall_time_ms=wall_ms,
        )
    except subprocess.TimeoutExpired as exc:
        wall_ms = (time.monotonic() - start) * 1000
        return SandboxResult(
            stdout=_to_text(exc.stdout),
            stderr=_to_text(exc.stderr),
            exit_code=-1,
            timed_out=True,
            wall_time_ms=wall_ms,
        )
    except FileNotFoundError:
        return SandboxResult(
            stdout="",
            stderr="docker not found; cannot run at sandbox level 3/4",
            exit_code=-1,
            timed_out=False,
            wall_time_ms=(time.monotonic() - start) * 1000,
        )
