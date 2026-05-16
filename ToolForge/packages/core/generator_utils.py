"""
ToolForge generator utilities — shared Jinja2 environment and rendering helpers.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, StrictUndefined, select_autoescape

# Resolved path to the templates directory
_TEMPLATES_ROOT = Path(__file__).parent.parent / "templates"

TOOLFORGE_VERSION = "0.1.0"


def _make_env(template_subdir: str) -> Environment:
    """Create a Jinja2 Environment scoped to *template_subdir*."""
    loader = FileSystemLoader(str(_TEMPLATES_ROOT / template_subdir))
    env = Environment(
        loader=loader,
        undefined=StrictUndefined,
        keep_trailing_newline=True,
        autoescape=select_autoescape([]),  # no HTML escaping for code generation
    )
    # Helpers available in all templates
    env.filters["tojson"] = lambda v, indent=None: json.dumps(v, indent=indent)
    return env


def render_template(template_subdir: str, template_name: str, ctx: dict[str, Any]) -> str:
    """Render a single Jinja2 template and return the result string."""
    env = _make_env(template_subdir)
    tpl = env.get_template(template_name)
    return tpl.render(**ctx)


def write_rendered(output_path: Path, content: str, overwrite: bool = False) -> bool:
    """
    Write *content* to *output_path*.
    Returns True if written, False if skipped (already exists + overwrite=False).
    """
    if output_path.exists() and not overwrite:
        raise FileExistsError(f"{output_path} already exists; use overwrite=True to replace it")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(content, encoding="utf-8")
    return True
