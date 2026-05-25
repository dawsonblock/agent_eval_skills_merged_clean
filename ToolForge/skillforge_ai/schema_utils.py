from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_schema(schema_name: str) -> dict[str, Any]:
    schema_path = Path(__file__).resolve().parent / "schemas" / schema_name
    return json.loads(schema_path.read_text(encoding="utf-8"))


def validate_with_schema(payload: Any, schema_name: str) -> None:
    from jsonschema import validate

    schema = load_schema(schema_name)
    validate(instance=payload, schema=schema)
