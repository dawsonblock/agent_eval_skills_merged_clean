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
    server_path: Path,
    tool_name: str,
    arguments: dict[str, str],
) -> dict[str, Any]:
    ctrl = MCPController()
    try:
        ctrl.start(server_path)
        return ctrl.call_tool(tool_name, arguments)
    finally:
        ctrl.stop()
