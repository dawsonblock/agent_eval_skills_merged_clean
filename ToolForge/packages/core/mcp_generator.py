"""
MCP server generator — renders an MCP server (Python or TypeScript) from a ToolSpec.

Creates:
  tools/generated/{slug}/mcp/
    ├── server.py  (Python)  OR  src/index.ts  (TypeScript)
    ├── pyproject.toml  OR  package.json
    └── Dockerfile
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from packages.core.tool_spec import ToolSpec, ToolLanguage
from packages.core.generator_utils import render_template, write_rendered, TOOLFORGE_VERSION


def _ctx(spec: ToolSpec) -> dict[str, Any]:
    return {"spec": spec, "toolforge_version": TOOLFORGE_VERSION}


def generate_mcp_server(spec: ToolSpec, output_root: Path, overwrite: bool = False) -> list[Path]:
    """
    Generate an MCP server in the language specified by ``spec.mcp.server_language``.
    Writes files under *output_root/mcp/*.
    """
    if not spec.mcp.enabled:
        return []

    mcp_dir = output_root / "mcp"
    mcp_dir.mkdir(parents=True, exist_ok=True)

    ctx = _ctx(spec)
    written: list[Path] = []

    if spec.mcp.server_language == ToolLanguage.TYPESCRIPT:
        (mcp_dir / "src").mkdir(exist_ok=True)
        files = [
            ("mcp_server_typescript", "index.ts.j2", mcp_dir / "src" / "index.ts"),
            ("mcp_server_typescript", "package.json.j2", mcp_dir / "package.json"),
        ]
    else:  # Python default
        # Copy tool.py stub too so server.py can import from it
        tool_src = output_root / "tool.py"
        if tool_src.exists():
            import shutil
            dst = mcp_dir / "tool.py"
            if not dst.exists() or overwrite:
                shutil.copy2(tool_src, dst)
                written.append(dst)

        files = [
            ("mcp_server_python", "server.py.j2", mcp_dir / "server.py"),
            ("mcp_server_python", "pyproject.toml.j2", mcp_dir / "pyproject.toml"),
        ]

    for tpl_dir, tpl_name, dest in files:
        content = render_template(tpl_dir, tpl_name, ctx)
        if write_rendered(dest, content, overwrite):
            written.append(dest)

    # Dockerfile (always Python-based for now, even for TS tools)
    dockerfile = mcp_dir / "Dockerfile"
    df_content = render_template("docker_template", "Dockerfile.j2", ctx)
    if write_rendered(dockerfile, df_content, overwrite):
        written.append(dockerfile)

    return written
