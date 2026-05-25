from __future__ import annotations
# mypy: disable-error-code=import-untyped

import json
import os
import signal
import subprocess  # nosec B404
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from skillforge_ai.config import ensure_runtime_state
from skillforge_ai.mcp_controller import MCPController


def _to_int(value: object, default: int = -1) -> int:
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            return default
    return default


def smoke_skill_server(server_path: Path) -> bool:
    ctrl = MCPController()
    return ctrl.smoke_test(server_path)


def list_profile_servers(workspace_root: Path, profile: str) -> list[str]:
    repo_root = workspace_root
    toolathlon_root = repo_root / "toolathlon-gym-curated"
    if not toolathlon_root.exists():
        parent_candidate = repo_root.parent / "toolathlon-gym-curated"
        if parent_candidate.exists():
            toolathlon_root = parent_candidate

    profile_file = toolathlon_root / "profiles" / profile / "mcp_servers.json"
    if not profile_file.exists():
        raise FileNotFoundError(f"Toolathlon profile file not found: {profile_file}")

    payload = json.loads(profile_file.read_text(encoding="utf-8"))
    servers = payload.get("servers", [])
    if not isinstance(servers, list):
        raise ValueError(f"Invalid profile structure in {profile_file}: 'servers' must be an array")
    return [str(item) for item in servers]


def list_running_servers(workspace_root: Path) -> list[dict[str, object]]:
    state = _read_state(workspace_root)
    out: list[dict[str, object]] = []
    for slug, data in state.items():
        pid = _to_int(data.get("pid", -1))
        running = _process_matches_entry(pid, data)
        out.append(
            {
                "slug": slug,
                "pid": pid,
                "server_path": str(data.get("server_path", "")),
                "started_at": str(data.get("started_at", "")),
                "running": running,
                "stdout_log": str(data.get("stdout_log", "")),
                "stderr_log": str(data.get("stderr_log", "")),
            }
        )
    return out


def start_managed_server(
    workspace_root: Path,
    slug: str,
    server_path: Path,
) -> dict[str, object]:
    state = _read_state(workspace_root)
    current = state.get(slug)
    if current is not None:
        current_pid = _to_int(current.get("pid", -1))
        if _process_matches_entry(current_pid, current):
            return {
                "slug": slug,
                "pid": current_pid,
                "already_running": True,
                "stdout_log": current.get("stdout_log", ""),
                "stderr_log": current.get("stderr_log", ""),
            }

    runs_dir = ensure_runtime_state(workspace_root).runs_dir
    log_dir = runs_dir / "mcp"
    log_dir.mkdir(parents=True, exist_ok=True)

    stdout_log = log_dir / f"{slug}.out.log"
    stderr_log = log_dir / f"{slug}.err.log"
    command = _build_server_command(server_path)

    stdout_fh = stdout_log.open("ab")
    stderr_fh = stderr_log.open("ab")
    try:
        proc = subprocess.Popen(
            command,
            cwd=str(server_path.parent),
            stdout=stdout_fh,
            stderr=stderr_fh,
            start_new_session=True,
        )  # nosec B603
    finally:
        stdout_fh.close()
        stderr_fh.close()

    time.sleep(0.4)
    if proc.poll() is not None:
        error_tail = ""
        if stderr_log.exists():
            error_tail = stderr_log.read_text(encoding="utf-8", errors="replace")[-500:]
        raise RuntimeError(
            f"MCP server exited immediately (code={proc.returncode})."
            + (f" stderr tail: {error_tail}" if error_tail else "")
        )

    entry = {
        "pid": proc.pid,
        "server_path": str(server_path),
        "command": command,
        "started_at": datetime.now(timezone.utc).isoformat(),
        "stdout_log": str(stdout_log),
        "stderr_log": str(stderr_log),
    }
    state[slug] = entry
    _write_state(workspace_root, state)

    return {
        "slug": slug,
        "pid": proc.pid,
        "already_running": False,
        "stdout_log": str(stdout_log),
        "stderr_log": str(stderr_log),
    }


def stop_managed_server(workspace_root: Path, slug: str) -> bool:
    state = _read_state(workspace_root)
    entry = state.get(slug)
    if entry is None:
        return False

    pid = _to_int(entry.get("pid", -1))
    if pid > 0 and _is_pid_running(pid):
        if not _process_matches_entry(pid, entry):
            raise RuntimeError(
                f"Refusing to stop pid={pid}: process does not match stored server metadata."
            )
        os.kill(pid, signal.SIGTERM)
        deadline = time.time() + 5.0
        while time.time() < deadline:
            if not _is_pid_running(pid):
                break
            time.sleep(0.1)
        if _is_pid_running(pid):
            os.kill(pid, signal.SIGKILL)

    state.pop(slug, None)
    _write_state(workspace_root, state)
    return True


def _build_server_command(server_path: Path) -> list[str]:
    ext = server_path.suffix.lower()
    if ext == ".py":
        return [sys.executable, str(server_path)]
    if ext in {".js", ".ts"}:
        return ["node", str(server_path)]
    return [sys.executable, str(server_path)]


def _state_file(workspace_root: Path) -> Path:
    return ensure_runtime_state(workspace_root).runs_dir / "mcp_processes.json"


def _read_state(workspace_root: Path) -> dict[str, dict[str, object]]:
    path = _state_file(workspace_root)
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    if isinstance(payload, dict):
        return {str(k): v for k, v in payload.items() if isinstance(v, dict)}
    return {}


def _write_state(workspace_root: Path, data: dict[str, dict[str, object]]) -> None:
    path = _state_file(workspace_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _is_pid_running(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def _process_matches_entry(pid: int, entry: dict[str, object]) -> bool:
    if not _is_pid_running(pid):
        return False

    cmdline = _pid_command_line(pid)
    if not cmdline:
        return False

    server_path = str(entry.get("server_path", "")).strip()
    if server_path and server_path not in cmdline:
        return False

    command = entry.get("command")
    if isinstance(command, list) and command:
        first = str(command[0]).strip()
        if first:
            first_name = Path(first).name
            if first_name and first_name not in cmdline:
                return False

    return True


def _pid_command_line(pid: int) -> str:
    try:
        completed = subprocess.run(
            ["ps", "-p", str(pid), "-o", "command="],
            capture_output=True,
            text=True,
            check=False,
        )
    except Exception:
        return ""

    if completed.returncode != 0:
        return ""
    return completed.stdout.strip()


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
