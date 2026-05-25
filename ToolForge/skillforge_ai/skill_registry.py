from __future__ import annotations

import json
from pathlib import Path
from typing import Any, List

from skillforge_ai.config import ensure_runtime_state
from skillforge_ai.schema_utils import validate_with_schema


class SkillRegistry:
    def __init__(self, workspace_root: Path) -> None:
        self._paths = ensure_runtime_state(workspace_root)
        self._path = self._paths.registry_path

    def list(self) -> List[dict[str, Any]]:
        return self._read()

    def get(self, name: str) -> dict[str, Any] | None:
        for entry in self._read():
            if entry.get("name") == name:
                return entry
        return None

    def upsert(self, entry: dict[str, Any]) -> None:
        data = self._read()
        out: list[dict[str, Any]] = []
        replaced = False
        for item in data:
            if item.get("name") == entry.get("name"):
                out.append(entry)
                replaced = True
            else:
                out.append(item)
        if not replaced:
            out.append(entry)
        self._write(out)

    def _read(self) -> List[dict[str, Any]]:
        try:
            payload = json.loads(self._path.read_text(encoding="utf-8"))
        except Exception:
            return []
        if not isinstance(payload, list):
            return []
        try:
            validate_with_schema(payload, "registry_schema.json")
        except Exception:
            return []
        return payload

    def _write(self, data: List[dict[str, Any]]) -> None:
        validate_with_schema(data, "registry_schema.json")
        self._path.write_text(
            json.dumps(data, indent=2) + "\n",
            encoding="utf-8",
        )
