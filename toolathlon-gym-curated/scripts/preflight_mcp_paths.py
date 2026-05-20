#!/usr/bin/env python3
"""Preflight validation for Toolathlon MCP server command paths.

Checks that all referenced MCP server binaries/scripts exist before runtime.
Resolves ${local_servers_paths} variable and validates command availability.

Exit codes:
  0 — all paths exist
  1 — one or more paths missing
"""
from __future__ import annotations

import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    print("ERROR: PyYAML required. Install with: pip install pyyaml", file=sys.stderr)
    sys.exit(1)


def load_mcp_configs(config_dir: Path) -> dict:
    """Load all YAML configs from configs/mcp_servers/."""
    configs: dict = {}
    if not config_dir.exists():
        print(f"ERROR: Config directory not found: {config_dir}", file=sys.stderr)
        return configs
    
    for yaml_file in sorted(config_dir.glob("*.yaml")):
        try:
            with yaml_file.open() as f:
                data = yaml.safe_load(f)
                configs[yaml_file.name] = data
        except Exception as e:
            print(f"ERROR: Failed to parse {yaml_file.name}: {e}", file=sys.stderr)
    
    return configs


def resolve_path(path_str: str, local_servers_dir: Path) -> str | None:
    """Resolve ${local_servers_paths} variable in path string."""
    if not isinstance(path_str, str):
        return None
    
    resolved = path_str.replace("${local_servers_paths}", str(local_servers_dir))
    return resolved


def extract_command_paths(config_name: str, config: dict, local_servers_dir: Path) -> list[tuple[str, str]]:
    """Extract all command paths from MCP server config.
    
    Returns list of (server_name, command_path) tuples.
    Handles both old and new config formats.
    """
    paths: list[tuple[str, str]] = []
    server_name = config.get("name", config_name.replace(".yaml", ""))
    
    # Check old format: mcpServers dict
    mcp_servers = config.get("mcpServers", {})
    if mcp_servers:
        for srv_name, srv_config in mcp_servers.items():
            if not isinstance(srv_config, dict):
                continue
            command = srv_config.get("command")
            args = srv_config.get("args", [])
            if command:
                resolved = resolve_path(command, local_servers_dir)
                if resolved:
                    paths.append((srv_name, resolved))
            if isinstance(args, list):
                for arg in args:
                    if isinstance(arg, str):
                        resolved = resolve_path(arg, local_servers_dir)
                        if resolved and any(resolved.endswith(ext) for ext in [".js", ".mjs", ".py"]):
                            paths.append((srv_name, resolved))
    
    # Check new format: params.command and params.args
    params = config.get("params", {})
    if isinstance(params, dict):
        command = params.get("command")
        args = params.get("args", [])
        
        # Process args for actual paths (not just the command like "node", "python", etc.)
        if isinstance(args, list):
            for arg in args:
                if isinstance(arg, str):
                    resolved = resolve_path(arg, local_servers_dir)
                    # Check if it looks like a path (starts with /, ${}, or has local_servers)
                    if resolved and (
                        resolved.endswith((".js", ".mjs", ".py")) or
                        "local_servers" in resolved or
                        "/" in resolved
                    ):
                        paths.append((server_name, resolved))
    
    return paths


def main() -> int:
    """Run preflight validation for all MCP servers."""
    # Find the repo root (parent of this script's parent)
    script_dir = Path(__file__).resolve().parent
    repo_root = script_dir.parent
    
    config_dir = repo_root / "configs" / "mcp_servers"
    local_servers_dir = repo_root / "local_servers"
    
    print(f"Checking MCP server paths in: {config_dir}")
    print(f"Local servers directory: {local_servers_dir}")
    print()
    
    configs = load_mcp_configs(config_dir)
    if not configs:
        print("WARNING: No MCP configs found", file=sys.stderr)
        return 0
    
    all_missing: list[tuple[str, str, str]] = []  # (config_name, server_name, path)
    all_found: list[tuple[str, str, str]] = []  # (config_name, server_name, path)
    
    for config_name, config in sorted(configs.items()):
        paths = extract_command_paths(config_name, config, local_servers_dir)
        
        for server_name, path_str in paths:
            path = Path(path_str)
            if path.exists():
                all_found.append((config_name, server_name, str(path)))
                print(f"✓ {server_name:30} {path}")
            else:
                all_missing.append((config_name, server_name, str(path)))
                print(f"✗ MISSING {server_name:24} {path}", file=sys.stderr)
    
    print()
    print(f"Found: {len(all_found)} paths")
    print(f"Missing: {len(all_missing)} paths")
    
    if all_missing:
        print("\nMISSING PATHS (required for Docker/production):")
        for config, server, path in all_missing:
            print(f"  {config}::{server} → {path}", file=sys.stderr)
        return 1
    
    print("\n✓ All MCP server paths valid.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
