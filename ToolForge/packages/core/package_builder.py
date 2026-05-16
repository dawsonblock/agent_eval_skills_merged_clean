"""
Package builder — bundles a generated tool into a distributable .zip archive.

Output: {dist_dir}/{slug}-{version}.zip

Archive layout:
  manifest.json           — spec + build metadata
  toolforge.yaml          — original spec file
  tool.py (or index.ts)   — entry point
  tests/                  — test suite
  mcp/                    — MCP server (if present)
  skills/                 — SKILL.md (if present)
  evals/                  — eval directory (if present)
"""
from __future__ import annotations

import json
import zipfile
from datetime import datetime, timezone
from pathlib import Path

from packages.core.tool_spec import ToolSpec


def build_package(
    spec: ToolSpec,
    tool_dir: Path,
    dist_dir: Path,
) -> Path:
    """
    Bundle *tool_dir* into *dist_dir/{slug}-{version}.zip*.
    Returns the path to the created archive.
    """
    dist_dir.mkdir(parents=True, exist_ok=True)
    archive_name = f"{spec.slug}-{spec.version}.zip"
    archive_path = dist_dir / archive_name

    # Build manifest
    manifest = {
        "name": spec.name,
        "slug": spec.slug,
        "version": spec.version,
        "description": spec.description,
        "language": spec.language.value,
        "built_at": datetime.now(timezone.utc).isoformat(),
        "toolforge_version": "0.1.0",
        "tags": spec.tags,
        "author": spec.author,
    }

    with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        # Write manifest
        zf.writestr("manifest.json", json.dumps(manifest, indent=2))

        # Walk the tool directory and add all files
        for file_path in sorted(tool_dir.rglob("*")):
            if file_path.is_file():
                # Skip Python cache and pytest artifacts
                parts = file_path.parts
                if any(p in ("__pycache__", ".pytest_cache", "node_modules") for p in parts):
                    continue
                if file_path.suffix in (".pyc", ".pyo"):
                    continue

                arc_name = file_path.relative_to(tool_dir)
                zf.write(file_path, arc_name)

    return archive_path
