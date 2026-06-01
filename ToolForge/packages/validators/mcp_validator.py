"""
MCP validator — validates a generated MCP server directory.

Checks:
  - server.py (Python) or src/index.ts (TS) exists
  - server.py is importable (Python only via py_compile)
  - Tool name registration matches spec
"""

from __future__ import annotations

import py_compile
from pathlib import Path

from packages.core.tool_spec import ToolSpec, ToolLanguage


class MCPValidationError(Exception):
    def __init__(self, errors: list[str]) -> None:
        self.errors = errors
        super().__init__("\n".join(errors))


def validate_mcp_server(spec: ToolSpec, mcp_dir: Path) -> list[str]:
    """
    Validate the MCP server directory at *mcp_dir*.
    Returns list of error strings (empty = valid).
    """
    errors: list[str] = []

    if not mcp_dir.exists():
        errors.append(f"MCP directory does not exist: {mcp_dir}")
        return errors

    if spec.mcp.server_language == ToolLanguage.TYPESCRIPT:
        ts_entry = mcp_dir / "src" / "index.ts"
        pkg_json = mcp_dir / "package.json"
        if not ts_entry.exists():
            errors.append(f"Missing TypeScript entry point: {ts_entry}")
        if not pkg_json.exists():
            errors.append(f"Missing package.json: {pkg_json}")
    else:
        server_py = mcp_dir / "server.py"
        if not server_py.exists():
            errors.append(f"Missing server.py: {server_py}")
        else:
            # Syntax check
            try:
                py_compile.compile(str(server_py), doraise=True)
            except py_compile.PyCompileError as exc:
                errors.append(f"server.py syntax error: {exc}")

            # Check tool name registration
            tool_name = spec.mcp.tool_name or spec.slug
            content = server_py.read_text(encoding="utf-8")
            if tool_name not in content:
                errors.append(
                    f"Tool name '{tool_name}' not found in server.py — "
                    "MCP server may not register the tool correctly"
                )

    return errors
