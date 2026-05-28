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
    except FileNotFoundError:
        duration = round(time.time() - started, 3)
        return {
            "target": target.name,
            "status": "failed",
            "reason": "missing_executable",
            "duration_seconds": duration,
            "command": shlex.join(target.command),
            "cwd": str(target.cwd),
            "stdout": "",
            "stderr": "Executable not found",
        }
    except PermissionError:
        duration = round(time.time() - started, 3)
        return {
            "target": target.name,
            "status": "failed",
            "reason": "permission_denied",
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
    with tempfile.TemporaryDirectory(prefix="mcp-smoke-") as tmp_dir:
        workspace_root = Path(tmp_dir)
        (workspace_root / "memory").mkdir(parents=True, exist_ok=True)
        targets = build_targets(workspace_root)

        try:
            profile_targets = load_profile_servers(REPO_ROOT, profile)
        except ProfileConfigError as exc:
            print(f"Profile configuration error: {exc}", file=sys.stderr)
            return 2

        selected_names = args.targets or profile_targets
        unknown = sorted(set(selected_names) - set(targets))
        if unknown:
            print(f"Unknown targets: {', '.join(unknown)}", file=sys.stderr)
            return 2

        results = [
            run_target(targets[name], args.timeout_seconds)
            for name in selected_names
        ]
        failed = [result for result in results if result["status"] != "passed"]

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
        }

        if args.json_output:
            args.json_output.parent.mkdir(parents=True, exist_ok=True)
            args.json_output.write_text(
                json.dumps(summary, indent=2) + "\n",
                encoding="utf-8",
            )

        print(json.dumps(summary, indent=2))
        if failed and strict_mode:
            return 1
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
