"""
Generates and validates JSON Schema documents from ToolSpec models.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from packages.core.tool_spec import ToolSpec


def build_toolforge_yaml_schema() -> dict[str, Any]:
    """
    Return the JSON Schema for toolforge.yaml files.
    This is used by ``toolforge validate`` to catch spec errors before generation.
    """
    # Emit Pydantic's own JSON schema for ToolSpec (v2 API)
    return ToolSpec.model_json_schema()


def save_toolforge_yaml_schema(output_path: Path) -> None:
    """Write the toolforge.yaml JSON Schema to *output_path*."""
    schema = build_toolforge_yaml_schema()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as fh:
        json.dump(schema, fh, indent=2)
        fh.write("\n")


def validate_spec_dict(data: dict[str, Any]) -> list[str]:
    """
    Validate a raw dictionary against the ToolSpec model.

    Returns a list of human-readable error strings (empty = valid).
    """
    from pydantic import ValidationError

    errors: list[str] = []
    try:
        ToolSpec.model_validate(data)
    except ValidationError as exc:
        for e in exc.errors():
            loc = " -> ".join(str(x) for x in e["loc"])
            errors.append(f"[{loc}] {e['msg']}")
    if errors:
        raise ValueError("Spec validation failed:\n" + "\n".join(errors))
    return errors
