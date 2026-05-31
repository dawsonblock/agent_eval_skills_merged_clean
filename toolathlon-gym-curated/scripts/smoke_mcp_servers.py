#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import os
import shlex
import subprocess
import sys
import tempfile
import textwrap
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from profile_utils import (
    ProfileConfigError,
    get_profile_name,
    load_profile_servers,
)


REPO_ROOT = Path(__file__).resolve().parent.parent
LOCAL_SERVERS_DIR = Path(
    os.environ.get("LOCAL_SERVERS_PATH", REPO_ROOT / "local_servers")
)

NODE_IMPORT_WRAPPER = textwrap.dedent(
    """
    import { pathToFileURL } from 'node:url';

    const entry = process.argv[1];

    try {
      await import(pathToFileURL(entry).href);
      process.exit(0);
    } catch (error) {
      console.error(error && error.stack ? error.stack : String(error));
      process.exit(1);
    }
    """
).strip()

FAILURE_MARKERS = (
    "Cannot find module",
    "ERR_MODULE_NOT_FOUND",
    "ModuleNotFoundError",
    "No module named",
    "ImportError",
)


@dataclass(frozen=True)
class SmokeTarget:
    name: str
    command: tuple[str, ...]
    cwd: Path
    env: dict[str, str]
    success_on_timeout: bool = True
    mcp_task: str | None = None


def build_targets(workspace_root: Path) -> dict[str, SmokeTarget]:
    local = LOCAL_SERVERS_DIR
    shared_env = {
        "PG_HOST": "postgres",
        "PG_PORT": "5432",
        "PG_DATABASE": "toolathlon",
        "PG_USER": "postgres",
        "PG_PASSWORD": "postgres",
    }

    return {
        "rail_12306": SmokeTarget(
            name="rail_12306",
            command=(
                "node",
                "--input-type=module",
                "-e",
                NODE_IMPORT_WRAPPER,
                str(local / "12306-mcp" / "build" / "index.js"),
            ),
            cwd=local / "12306-mcp",
            env=shared_env,
            mcp_task="rail_12306_health",
        ),
        "filesystem": SmokeTarget(
            name="filesystem",
            command=(
                "node",
                "--input-type=module",
                "-e",
                NODE_IMPORT_WRAPPER,
                str(local / "filesystem" / "dist" / "index.js"),
            ),
            cwd=local / "filesystem",
            env={},
            mcp_task="filesystem_list",
        ),
        "google_calendar": SmokeTarget(
            name="google_calendar",
            command=(
                "node",
                "--input-type=module",
                "-e",
                NODE_IMPORT_WRAPPER,
                str(
                    local
                    / "Calendar-Autoauth-MCP-Server"
                    / "build"
                    / "index.js"
                ),
            ),
            cwd=workspace_root,
            env={},
        ),
        "canvas": SmokeTarget(
            name="canvas",
            command=(
                "node",
                "--input-type=module",
                "-e",
                NODE_IMPORT_WRAPPER,
                str(local / "mcp-canvas-lms" / "build" / "index.js"),
            ),
            cwd=workspace_root,
            env={
                **shared_env,
                "CANVAS_API_TOKEN": "placeholder",
                "CANVAS_DOMAIN": "localhost:8080",
                "NODE_TLS_REJECT_UNAUTHORIZED": "0",
            },
        ),
        "howtocook": SmokeTarget(
            name="howtocook",
            command=(
                "node",
                "--input-type=module",
                "-e",
                NODE_IMPORT_WRAPPER,
                str(local / "HowToCook-mcp" / "build" / "index.js"),
            ),
            cwd=workspace_root,
            env={},
        ),
        "memory": SmokeTarget(
            name="memory",
            command=(
                "node",
                "--input-type=module",
                "-e",
                NODE_IMPORT_WRAPPER,
                str(
                    local / "servers" / "src" / "memory" / "dist" / "index.js"
                ),
            ),
            cwd=workspace_root,
            env={
                "MEMORY_FILE_PATH": str(
                    workspace_root / "memory" / "memory.json"
                )
            },
        ),
        "google_forms": SmokeTarget(
            name="google_forms",
            command=(
                "node",
                "--input-type=module",
                "-e",
                NODE_IMPORT_WRAPPER,
                str(local / "google-forms-mcp" / "build" / "index.js"),
            ),
            cwd=workspace_root,
            env={},
        ),
        "fetch": SmokeTarget(
            name="fetch",
            command=(
                "node",
                "--input-type=module",
                "-e",
                NODE_IMPORT_WRAPPER,
                str(local / "mcp-npx-fetch" / "dist" / "index.js"),
            ),
            cwd=workspace_root,
            env={},
        ),
        "notion": SmokeTarget(
            name="notion",
            command=(
                "node",
                "--input-type=module",
                "-e",
                NODE_IMPORT_WRAPPER,
                str(local / "notion-mcp-server" / "bin" / "cli.mjs"),
            ),
            cwd=workspace_root,
            env={
                "OPENAPI_MCP_HEADERS": (
                    '{"Authorization": "Bearer ntn-placeholder", '
                    '"Notion-Version": "2022-06-28"}'
                ),
            },
        ),
        "woocommerce": SmokeTarget(
            name="woocommerce",
            command=(
                "node",
                "--input-type=module",
                "-e",
                NODE_IMPORT_WRAPPER,
                str(local / "woocommerce-mcp" / "dist" / "index.js"),
            ),
            cwd=workspace_root,
            env={
                **shared_env,
                "WORDPRESS_SITE_URL": "http://localhost:8081",
                "WOOCOMMERCE_CONSUMER_KEY": "placeholder",
                "WOOCOMMERCE_CONSUMER_SECRET": "placeholder",
            },
        ),
        "youtube": SmokeTarget(
            name="youtube",
            command=(
                "node",
                "--input-type=module",
                "-e",
                NODE_IMPORT_WRAPPER,
                str(local / "youtube-mcp-server" / "dist" / "index.js"),
            ),
            cwd=workspace_root,
            env=shared_env,
        ),
        "youtube_transcript": SmokeTarget(
            name="youtube_transcript",
            command=(
                str(
                    local
                    / "mcp-youtube-transcript"
                    / ".venv"
                    / "bin"
                    / "python3"
                ),
                "-c",
                "import mcp_youtube_transcript",
            ),
            cwd=local / "mcp-youtube-transcript",
            env=shared_env,
            success_on_timeout=True,
        ),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Smoke-test built MCP server artifacts for immediate dependency "
            "and runtime failures."
        )
    )
    parser.add_argument(
        "--target",
        action="append",
        dest="targets",
        help=(
            "Target name to test. Repeat to run multiple targets. "
            "Defaults to all required artifact builders."
        ),
    )
    parser.add_argument(
        "--timeout-seconds",
        type=float,
        default=5.0,
        help=(
            "Timeout per target. Timeouts count as success for long-running "
            "server entrypoints."
        ),
    )
    parser.add_argument(
        "--json-output",
        type=Path,
        help="Optional path for a machine-readable summary.",
    )
    parser.add_argument(
        "--profile",
        type=str,
        default=None,
        help=(
            "Validation profile to use (defaults to TOOLATHLON_PROFILE or "
            "'smoke')."
        ),
    )
    parser.add_argument(
        "--strict",
        dest="strict",
        action="store_true",
        default=None,
        help="Fail command with non-zero exit if any target fails.",
    )
    parser.add_argument(
        "--no-strict",
        dest="strict",
        action="store_false",
        help="Always return zero even when some targets fail.",
    )
    return parser.parse_args()


def classify_failure(output: str) -> str:
    for marker in FAILURE_MARKERS:
        if marker in output:
            return "dependency_resolution_failed"
    return "startup_failed"


def execute_mcp_task(
    target: SmokeTarget, timeout_seconds: float
) -> dict[str, Any]:
    if not target.mcp_task:
        return {
            "target": target.name,
            "status": "skipped",
            "reason": "no_mcp_task_configured",
        }
    env = os.environ.copy()
    env.update(target.env)
    target.cwd.mkdir(parents=True, exist_ok=True)
    initialize = {
        "jsonrpc": "2.0",
        "id": 0,
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "smoke-task", "version": "0.1.0"},
        },
    }
    initialized = {"jsonrpc": "2.0", "method": "notifications/initialized"}
    task_messages = {
        "filesystem_list": [
            {"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}},
            {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/call",
                "params": {
                    "name": "list_allowed_directories",
                    "arguments": {},
                },
            },
        ],
        "rail_12306_health": [
            {"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}},
        ],
    }
    messages = task_messages.get(target.mcp_task, [])
    if not messages:
        return {
            "target": target.name,
            "status": "skipped",
            "reason": "unknown_mcp_task",
            "task": target.mcp_task,
        }
    all_messages = [initialize, initialized] + messages
    input_lines = [json.dumps(msg) for msg in all_messages]
    stdin_data = "\n".join(input_lines) + "\n"
    started = time.time()
    try:
        completed = subprocess.run(
            target.command,
            cwd=target.cwd,
            env=env,
            input=stdin_data,
            capture_output=True,
            text=True,
            timeout=timeout_seconds * 2,
            check=False,
        )
    except (FileNotFoundError, PermissionError, subprocess.TimeoutExpired) as exc:
        duration = round(time.time() - started, 3)
        reason = "missing_executable"
        if isinstance(exc, PermissionError):
            reason = "permission_denied"
        elif isinstance(exc, subprocess.TimeoutExpired):
            reason = "task_timeout"
        return {
            "target": target.name,
            "status": "failed",
            "reason": reason,
            "task": target.mcp_task,
            "duration_seconds": duration,
            "error": str(exc),
        }
    duration = round(time.time() - started, 3)
    stdout = completed.stdout or ""
    stderr = completed.stderr or ""
    responses = []
    for line in stdout.strip().split("\n"):
        line = line.strip()
        if line.startswith("{"):
            try:
                responses.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    task_ok = any(
        isinstance(r, dict) and "result" in r for r in responses
    )
    db_unavailable = "postgres" in stderr.lower() or "connection" in stderr.lower()
    if task_ok:
        return {
            "target": target.name,
            "status": "passed",
            "reason": "task_executed",
            "task": target.mcp_task,
            "duration_seconds": duration,
            "response_count": len(responses),
        }
    if db_unavailable:
        return {
            "target": target.name,
            "status": "degraded",
            "reason": "database_unavailable",
            "task": target.mcp_task,
            "duration_seconds": duration,
            "warning": "PostgreSQL not available; task-smoke degraded to import-smoke",
        }
    return {
        "target": target.name,
        "status": "failed",
        "reason": "task_response_missing",
        "task": target.mcp_task,
        "duration_seconds": duration,
        "stdout_tail": stdout[-500:],
        "stderr_tail": stderr[-500:],
    }


def output_text(value: object) -> str:
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return str(value or "")


def run_target(
    target: SmokeTarget, timeout_seconds: float
) -> dict[str, Any]:
    env = os.environ.copy()
    env.update(target.env)
    target.cwd.mkdir(parents=True, exist_ok=True)

    started = time.time()
    try:
        completed = subprocess.run(
            target.command,
            cwd=target.cwd,
            env=env,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
        )
    except FileNotFoundError as exc:
        duration = round(time.time() - started, 3)
        return {
            "target": target.name,
            "server": target.name,
            "status": "fail",
            "reason": "missing_executable",
            "error": str(exc),
            "path": target.command[0] if target.command else "",
            "duration_seconds": duration,
            "command": shlex.join(target.command),
            "cwd": str(target.cwd),
            "stdout": "",
            "stderr": "Executable not found",
        }
    except PermissionError as exc:
        duration = round(time.time() - started, 3)
        return {
            "target": target.name,
            "server": target.name,
            "status": "fail",
            "reason": "permission_denied",
            "error": str(exc),
            "path": target.command[0] if target.command else "",
            "duration_seconds": duration,
            "command": shlex.join(target.command),
            "cwd": str(target.cwd),
            "stdout": "",
            "stderr": "Permission denied while launching executable",
        }
    except subprocess.TimeoutExpired as exc:
        duration = round(time.time() - started, 3)
        status = "passed" if target.success_on_timeout else "failed"
        result: dict[str, Any] = {
            "target": target.name,
            "server": target.name,
            "status": status,
            "reason": (
                "startup_timeout"
                if target.success_on_timeout
                else "timeout"
            ),
            "duration_seconds": duration,
            "command": shlex.join(target.command),
            "cwd": str(target.cwd),
            "stdout": output_text(exc.stdout)[-4000:],
            "stderr": output_text(exc.stderr)[-4000:],
        }
        return result

    duration = round(time.time() - started, 3)
    stdout = completed.stdout[-4000:]
    stderr = completed.stderr[-4000:]
    combined = "\n".join(part for part in (stdout, stderr) if part)

    if completed.returncode == 0:
        return {
            "target": target.name,
            "server": target.name,
            "status": "passed",
            "reason": "started_or_imported",
            "duration_seconds": duration,
            "command": shlex.join(target.command),
            "cwd": str(target.cwd),
            "stdout": stdout,
            "stderr": stderr,
        }

    return {
        "target": target.name,
        "server": target.name,
        "status": "failed",
        "reason": classify_failure(combined),
        "duration_seconds": duration,
        "returncode": completed.returncode,
        "command": shlex.join(target.command),
        "cwd": str(target.cwd),
        "stdout": stdout,
        "stderr": stderr,
    }


def main() -> int:
    args = parse_args()
    profile = (args.profile or get_profile_name()).strip() or "smoke"
    strict_mode = args.strict if args.strict is not None else profile == "smoke"

    def write_summary(path: Path | None, payload: dict[str, Any]) -> None:
        if path is None:
            return
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    with tempfile.TemporaryDirectory(prefix="mcp-smoke-") as tmp_dir:
        workspace_root = Path(tmp_dir)
        (workspace_root / "memory").mkdir(parents=True, exist_ok=True)
        targets = build_targets(workspace_root)

        try:
            profile_targets = load_profile_servers(REPO_ROOT, profile)
        except ProfileConfigError as exc:
            print(f"Profile configuration error: {exc}", file=sys.stderr)
            summary = {
                "checked_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "profile": profile,
                "strict_mode": strict_mode,
                "target_count": 0,
                "passed_count": 0,
                "failed_count": 1,
                "overall_status": "failed",
                "error": str(exc),
                "results": [],
            }
            write_summary(args.json_output, summary)
            print(json.dumps(summary, indent=2))
            return 2

        selected_names = args.targets or profile_targets
        unknown = sorted(set(selected_names) - set(targets))
        if unknown:
            print(f"Unknown targets: {', '.join(unknown)}", file=sys.stderr)
            summary = {
                "checked_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "profile": profile,
                "strict_mode": strict_mode,
                "target_count": 0,
                "passed_count": 0,
                "failed_count": len(unknown),
                "overall_status": "failed",
                "error": f"Unknown targets: {', '.join(unknown)}",
                "results": [],
            }
            write_summary(args.json_output, summary)
            print(json.dumps(summary, indent=2))
            return 2

        results = [
            run_target(targets[name], args.timeout_seconds)
            for name in selected_names
        ]
        task_results = []
        for name in selected_names:
            t = targets[name]
            startup = next(r for r in results if r["target"] == name)
            if startup["status"] == "passed" and t.mcp_task:
                task_result = execute_mcp_task(t, args.timeout_seconds)
                task_results.append(task_result)
        failed = [result for result in results if result["status"] != "passed"]
        task_degraded = [
            r for r in task_results if r["status"] == "degraded"
        ]
        task_failed = [
            r for r in task_results if r["status"] == "failed"
        ]

        summary = {
            "checked_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "profile": profile,
            "strict_mode": strict_mode,
            "local_servers_dir": str(LOCAL_SERVERS_DIR),
            "target_count": len(results),
            "passed_count": len(results) - len(failed),
            "failed_count": len(failed),
            "overall_status": "passed" if not failed else "failed",
            "results": results,
            "task_smoke": {
                "executed": len(task_results),
                "passed": len([r for r in task_results if r["status"] == "passed"]),
                "degraded": len(task_degraded),
                "failed": len(task_failed),
                "details": task_results,
            },
        }

        write_summary(args.json_output, summary)

        print(json.dumps(summary, indent=2))
        if failed and strict_mode:
            return 1
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
