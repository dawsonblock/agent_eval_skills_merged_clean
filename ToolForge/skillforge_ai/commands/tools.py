from __future__ import annotations

from pathlib import Path
from typing import Any

from skillforge_ai.mcp_controller import MCPController
from skillforge_ai.tool_registry import SkillForgeRegistry


def list_registry_tools(workspace_root: Path) -> list[dict[str, Any]]:
    return SkillForgeRegistry(workspace_root).list_registered_tools()


def list_mcp_tools(server_path: Path) -> list[dict[str, Any]]:
    ctrl = MCPController()
    try:
        ctrl.start(server_path)
        return ctrl.list_tools()
    finally:
        ctrl.stop()


def call_mcp_tool(
    workspace_root: Path,
    slug: str,
    server_path: Path,
    tool_name: str,
    arguments: dict[str, str],
) -> dict[str, Any]:
    registry = SkillForgeRegistry(workspace_root)
    registered = registry.get_registered_tool(tool_name)
    if registered is None:
        fallback_name = f"{slug}_tool"
        registered = registry.get_registered_tool(fallback_name)

    if registered is None:
        raise ValueError(
            f"Tool '{tool_name}' is not in the SkillForge tool registry for '{slug}'. "
            "Register/install the tool before calling it."
        )

    declared_server = registered.get("mcp_server")
    if isinstance(declared_server, str) and declared_server.strip():
        declared_path = Path(declared_server).resolve()
        if declared_path != server_path.resolve():
            raise ValueError(
                "Requested server path does not match registry metadata for this tool."
            )

    ctrl = MCPController()
    try:
        ctrl.start(server_path)
        return ctrl.call_tool(tool_name, arguments)
    finally:
        ctrl.stop()
