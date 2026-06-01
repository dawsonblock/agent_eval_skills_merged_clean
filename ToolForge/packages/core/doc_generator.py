"""
Doc generator — renders README.md (and future API docs) from a ToolSpec.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from packages.core.tool_spec import ToolSpec
from packages.core.generator_utils import render_template, write_rendered, TOOLFORGE_VERSION


def generate_docs(spec: ToolSpec, output_root: Path, overwrite: bool = False) -> list[Path]:
    """
    Render README.md into *output_root/{spec.slug}/*.
    """
    doc_dir = output_root / spec.slug
    doc_dir.mkdir(parents=True, exist_ok=True)

    ctx: dict[str, Any] = {"spec": spec, "toolforge_version": TOOLFORGE_VERSION}
    content = render_template("readme_template", "README.md.j2", ctx)

    dest = doc_dir / "README.md"
    if write_rendered(dest, content, overwrite):
        return [dest]
    return []
