"""
config_bridge — map toolathlon-gym MCP server YAML configs to ToolForge constructs.
"""
from __future__ import annotations

from pathlib import Path

from packages.core.tool_spec import MCPSpec, ToolLanguage, ToolSpec


def load_toolathlon_config(config_path: Path) -> dict[str, object]:
    """Return a toolathlon MCP server config as a plain dict."""
    import yaml  # noqa: PLC0415

    return yaml.safe_load(config_path.read_text(encoding="utf-8"))


def toolathlon_config_to_mcp_spec(config: dict[str, object]) -> MCPSpec:
    """
    Convert a toolathlon server config dict to a ToolForge MCPSpec.

    Toolathlon config example::
      name: arxiv-local
      command: python
      args: ["-m", "arxiv_mcp"]
      env: {}
      transport: stdio
    """
    transport = config.get("transport", "stdio")
    return MCPSpec(
        enabled=True,
        transport=transport,
    )


def toolathlon_config_to_partial_spec(config: dict[str, object], slug: str | None = None) -> ToolSpec:
    """
    Build a minimal ToolSpec from a toolathlon MCP server config.
    Useful for importing toolathlon server configs into the ToolForge registry.
    """
    name = config.get("name", slug or "toolathlon-tool")
    _slug = slug or name.lower().replace(" ", "-").replace("_", "-")
    command = config.get("command", "python")
    language = ToolLanguage.PYTHON if "python" in command else ToolLanguage.TYPESCRIPT

    return ToolSpec(
        name=name,
        slug=_slug,
        version="0.1.0",
        description=config.get("description", f"Imported from toolathlon: {name}"),
        language=language,
        entry_point=config.get("args", [""])[0] if config.get("args") else "server.py",
        mcp=toolathlon_config_to_mcp_spec(config),
    )
