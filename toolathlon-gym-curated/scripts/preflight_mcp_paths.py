#!/usr/bin/env python3
"""Preflight validation for Toolathlon MCP server command paths.

Checks that all referenced MCP server binaries/scripts exist before runtime.
Resolves ${local_servers_paths} variable and validates command availability.

Exit codes:
  0 — all paths exist
  1 — one or more paths missing
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:
    print(
        "ERROR: PyYAML required. Install with: pip install pyyaml",
        file=sys.stderr,
    )
    sys.exit(1)


def load_mcp_configs(config_dir: Path) -> dict[str, Any]:
    """Load all YAML configs from configs/mcp_servers/."""
    configs: dict[str, Any] = {}
    if not config_dir.exists():
        print(
            f"ERROR: Config directory not found: {config_dir}",
            file=sys.stderr,
        )
        return configs

    for yaml_file in sorted(config_dir.glob("*.yaml")):
        try:
            with yaml_file.open() as f:
                data = yaml.safe_load(f)
                configs[yaml_file.name] = data
        except Exception as e:
            print(
                f"ERROR: Failed to parse {yaml_file.name}: {e}",
                file=sys.stderr,
            )

    return configs


def resolve_path(path_str: str, local_servers_dir: Path) -> str | None:
    """Resolve ${local_servers_paths} variable in path string."""
    if not isinstance(path_str, str):
        return None

    resolved = path_str.replace(
        "${local_servers_paths}", str(local_servers_dir)
    )
    return resolved


def is_runtime_placeholder(value: str) -> bool:
    """Return True for placeholders that are resolved only at task runtime."""
    return "${agent_workspace}" in value or "${task_dir}" in value


def looks_like_executable_path(value: str) -> bool:
    """Return True for strings that look like executable/script paths."""
    if not value or " " in value:
        return False
    if value.startswith(("http://", "https://")):
        return False
    if is_runtime_placeholder(value):
        return False
    if value in {"node", "python", "python3", "uv", "npm", "bash", "sh"}:
        return False
    if value.endswith((".js", ".mjs", ".py", ".sh")):
        return True
    return "/" in value


def to_path(
    value: str, base_dir: Path, local_servers_dir: Path
) -> Path | None:
    """Resolve a candidate path string to an absolute Path when possible."""
    resolved = resolve_path(value, local_servers_dir)
    if not resolved or not looks_like_executable_path(resolved):
        return None
    p = Path(resolved)
    if p.is_absolute():
        return p
    return (base_dir / p).resolve()


def path_exists(path: Path) -> bool:
    """Return True if path exists, with python/python3 venv alias fallback."""
    if path.exists():
        return True
    if str(path).endswith("/.venv/bin/python3"):
        alt = Path(str(path)[:-1])
        return alt.exists()
    if str(path).endswith("/.venv/bin/python"):
        alt = Path(f"{path}3")
        return alt.exists()
    return False


def extract_command_paths(
    config_name: str,
    config: dict[str, Any],
    local_servers_dir: Path,
) -> list[tuple[str, str]]:
    """Extract all command paths from MCP server config.

    Return a list of (server_name, command_path) tuples.
    Handles both old and new config formats.
    """
    paths: list[tuple[str, str]] = []
    server_name = config.get("name", config_name.replace(".yaml", ""))
    config_base = local_servers_dir

    # Check old format: mcpServers dict
    mcp_servers = config.get("mcpServers", {})
    if mcp_servers:
        for srv_name, srv_config in mcp_servers.items():
            if not isinstance(srv_config, dict):
                continue
            srv_cwd = srv_config.get("cwd")
            base_dir = config_base
            if isinstance(srv_cwd, str):
                resolved_cwd = resolve_path(srv_cwd, local_servers_dir)
                if resolved_cwd and not is_runtime_placeholder(resolved_cwd):
                    cwd_path = Path(resolved_cwd)
                    if cwd_path.is_absolute():
                        base_dir = cwd_path
                    else:
                        base_dir = (config_base / cwd_path).resolve()
            command = srv_config.get("command")
            args = srv_config.get("args", [])
            if isinstance(command, str):
                cmd_path = to_path(command, base_dir, local_servers_dir)
                if cmd_path is not None:
                    paths.append((srv_name, str(cmd_path)))
            if isinstance(args, list):
                for arg in args:
                    if isinstance(arg, str):
                        arg_path = to_path(arg, base_dir, local_servers_dir)
                        if arg_path is not None:
                            paths.append((srv_name, str(arg_path)))

    # Check new format: params.command and params.args
    params = config.get("params", {})
    if isinstance(params, dict):
        params_cwd = params.get("cwd")
        base_dir = config_base
        if isinstance(params_cwd, str):
            resolved_cwd = resolve_path(params_cwd, local_servers_dir)
            if resolved_cwd and not is_runtime_placeholder(resolved_cwd):
                cwd_path = Path(resolved_cwd)
                if cwd_path.is_absolute():
                    base_dir = cwd_path
                else:
                    base_dir = (config_base / cwd_path).resolve()

        command = params.get("command")
        args = params.get("args", [])
        runtime_base = base_dir

        if isinstance(args, list):
            for idx, arg in enumerate(args):
                if (
                    arg in {"--directory", "--cwd", "-C"}
                    and idx + 1 < len(args)
                ):
                    dir_arg = args[idx + 1]
                    if isinstance(dir_arg, str):
                        dir_path = to_path(
                            dir_arg, base_dir, local_servers_dir
                        )
                        if dir_path is not None and dir_path.exists():
                            runtime_base = dir_path

        if isinstance(command, str):
            cmd_path = to_path(command, base_dir, local_servers_dir)
            if cmd_path is not None:
                paths.append((server_name, str(cmd_path)))

        if isinstance(args, list):
            for idx, arg in enumerate(args):
                if isinstance(arg, str):
                    base_for_arg = runtime_base
                    if idx > 0 and args[idx - 1] in {
                        "python",
                        "python3",
                        "node",
                    }:
                        base_for_arg = runtime_base
                    arg_path = to_path(arg, base_for_arg, local_servers_dir)
                    if arg_path is not None:
                        paths.append((server_name, str(arg_path)))

    return paths


def write_json_output(
    output_path: Path,
    config_dir: Path,
    local_servers_dir: Path,
    all_found: list[tuple[str, str, str]],
    all_missing: list[tuple[str, str, str]],
) -> None:
    """Write a machine-readable preflight summary file."""
    payload = {
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "config_dir": str(config_dir.resolve()),
        "local_servers_dir": str(local_servers_dir),
        "found_count": len(all_found),
        "missing_count": len(all_missing),
        "found": [
            {"config": config, "server": server, "path": path}
            for config, server, path in all_found
        ],
        "missing": [
            {"config": config, "server": server, "path": path}
            for config, server, path in all_missing
        ],
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    """Run preflight validation for all MCP servers."""
    parser = argparse.ArgumentParser(
        description="Validate MCP command paths before runtime"
    )
    parser.add_argument(
        "--json-output",
        type=Path,
        default=None,
        help="Optional path to write a machine-readable JSON summary",
    )
    args = parser.parse_args()

    # Find the repo root (parent of this script's parent)
    script_dir = Path(__file__).resolve().parent
    repo_root = script_dir.parent

    config_dir = repo_root / "configs" / "mcp_servers"
    local_servers_dir = Path(
        os.environ.get("LOCAL_SERVERS_PATH", str(repo_root / "local_servers"))
    ).resolve()

    print(f"Checking MCP server paths in: {config_dir.resolve()}")
    print(f"Local servers directory: {local_servers_dir}")
    print()

    configs = load_mcp_configs(config_dir)
    if not configs:
        print("WARNING: No MCP configs found", file=sys.stderr)
        return 0

    # (config_name, server_name, path)
    all_missing: list[tuple[str, str, str]] = []
    all_found: list[tuple[str, str, str]] = []

    for config_name, config in sorted(configs.items()):
        paths = extract_command_paths(config_name, config, local_servers_dir)

        for server_name, path_str in paths:
            path = Path(path_str)
            if path_exists(path):
                all_found.append((config_name, server_name, str(path)))
                print(f"✓ {server_name:30} {path}")
            else:
                all_missing.append((config_name, server_name, str(path)))
                print(f"✗ MISSING {server_name:24} {path}", file=sys.stderr)

    print()
    print(f"Found: {len(all_found)} paths")
    print(f"Missing: {len(all_missing)} paths")

    if args.json_output is not None:
        write_json_output(
            args.json_output,
            config_dir,
            local_servers_dir,
            all_found,
            all_missing,
        )
        print(f"JSON summary: {args.json_output}")

    if all_missing:
        print("\nMISSING PATHS (required for Docker/production):")
        for config, server, path_text in all_missing:
            print(f"  {config}::{server} → {path_text}", file=sys.stderr)
        return 1

    print("\n✓ All MCP server paths valid.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
