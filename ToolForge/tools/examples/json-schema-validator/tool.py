"""
json-schema-validator — validates JSON data against a JSON Schema.

Inputs (via TOOLFORGE_INPUTS env var, JSON dict):
  data    (str, required) — JSON string or path to a JSON file
  schema  (str, required) — JSON Schema string or path to a JSON Schema file

Output: JSON string with 'valid' boolean and 'errors' list.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path


def _load_json(value: str) -> object:
    """Try to parse *value* as JSON; if it looks like a path, read the file first."""
    stripped = value.strip()
    if stripped.startswith(("{", "[", '"', "t", "f", "n") or stripped[0:1].isdigit()):
        return json.loads(stripped)
    # Treat as file path
    p = Path(stripped)
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8"))
    # Last attempt — parse as-is
    return json.loads(stripped)


def validate_json(data_raw: str, schema_raw: str) -> dict:
    try:
        import jsonschema  # noqa: PLC0415
    except ImportError:
        return {
            "valid": False,
            "errors": ["jsonschema package not installed — run: pip install jsonschema"],
        }

    try:
        data = _load_json(data_raw)
    except (json.JSONDecodeError, FileNotFoundError) as e:
        return {"valid": False, "errors": [f"Failed to parse data: {e}"]}

    try:
        schema = _load_json(schema_raw)
    except (json.JSONDecodeError, FileNotFoundError) as e:
        return {"valid": False, "errors": [f"Failed to parse schema: {e}"]}

    validator = jsonschema.Draft7Validator(schema)
    errors = [e.message for e in sorted(validator.iter_errors(data), key=str)]

    return {
        "valid": len(errors) == 0,
        "errors": errors,
    }


def main() -> None:
    raw = os.environ.get("TOOLFORGE_INPUTS", "{}")
    try:
        inputs = json.loads(raw)
    except json.JSONDecodeError as e:
        print(f"Error parsing inputs: {e}", file=sys.stderr)
        sys.exit(1)

    data_raw = inputs.get("data")
    schema_raw = inputs.get("schema")

    if not data_raw:
        print("Error: 'data' is required.", file=sys.stderr)
        sys.exit(1)
    if not schema_raw:
        print("Error: 'schema' is required.", file=sys.stderr)
        sys.exit(1)

    result = validate_json(data_raw, schema_raw)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
