"""
ToolRegistry — persistent index of registered ToolForge tools.

Registry file: toolforge_registry.json (in the ToolForge workspace root).
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Iterator

from packages.core.tool_spec import ToolSpec


class ToolRegistry:
    """Load/save a flat JSON registry of tool specs."""

    def __init__(self, registry_path: Path) -> None:
        self._path = registry_path
        self._entries: dict[str, dict] = {}
        if registry_path.exists():
            self._entries = json.loads(registry_path.read_text(encoding="utf-8"))

    # ------------------------------------------------------------------
    # Mutation
    # ------------------------------------------------------------------

    def register(self, spec: ToolSpec) -> None:
        """Add or update a tool spec in the registry."""
        self._entries[spec.slug] = json.loads(spec.model_dump_json())
        self._save()

    def deregister(self, slug: str) -> bool:
        """Remove *slug* from the registry.  Returns True if it existed."""
        existed = slug in self._entries
        self._entries.pop(slug, None)
        if existed:
            self._save()
        return existed

    # ------------------------------------------------------------------
    # Querying
    # ------------------------------------------------------------------

    def find(self, slug: str) -> ToolSpec | None:
        """Return the ToolSpec for *slug*, or None if not registered."""
        data = self._entries.get(slug)
        if data is None:
            return None
        return ToolSpec.model_validate(data)

    def list_all(self) -> list[ToolSpec]:
        """Return all registered tool specs."""
        return [ToolSpec.model_validate(v) for v in self._entries.values()]

    def search_by_tag(self, tag: str) -> list[ToolSpec]:
        """Return specs whose tags include *tag* (case-insensitive)."""
        tag_lower = tag.lower()
        return [
            ToolSpec.model_validate(v)
            for v in self._entries.values()
            if any(t.lower() == tag_lower for t in v.get("tags", []))
        ]

    def __iter__(self) -> Iterator[ToolSpec]:
        return iter(self.list_all())

    def __len__(self) -> int:
        return len(self._entries)

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(
            json.dumps(self._entries, indent=2, default=str),
            encoding="utf-8",
        )
