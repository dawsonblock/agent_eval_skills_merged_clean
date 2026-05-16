"""
Schema validator — validates a toolforge.yaml file against the ToolSpec JSON Schema.
"""
from __future__ import annotations

from pathlib import Path

from packages.core.tool_schema import validate_spec_dict
from packages.core.tool_spec import ToolSpec


class SchemaValidationError(Exception):
    def __init__(self, errors: list[str]) -> None:
        self.errors = errors
        super().__init__("\n".join(errors))


def validate_yaml_file(yaml_path: Path) -> ToolSpec:
    """
    Load and validate *yaml_path* as a ToolSpec.

    Returns the validated ToolSpec on success.
    Raises SchemaValidationError listing all field errors on failure.
    """
    from ruamel.yaml import YAML

    yaml = YAML(typ="safe")
    with open(yaml_path, "r") as fh:
        data = yaml.load(fh) or {}

    try:
        errors = validate_spec_dict(data)
    except ValueError as exc:
        msgs = [line for line in str(exc).splitlines() if line and not line.startswith("Spec")]
        raise SchemaValidationError(msgs or [str(exc)]) from exc
    if errors:
        raise SchemaValidationError(errors)

    return ToolSpec.model_validate(data)
