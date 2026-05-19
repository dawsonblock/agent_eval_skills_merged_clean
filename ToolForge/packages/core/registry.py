"""
ToolRegistry — persistent index of registered ToolForge tools.

Registry file: toolforge_registry.json (in the ToolForge workspace root).

Each entry tracks:
  - spec: the full ToolSpec
  - metadata: {status, eval_score, last_run, last_validation, paths, ...}
"""
from __future__ import annotations

import json
import logging
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator, Literal

from packages.core.tool_spec import ToolSpec
from pydantic import ValidationError

# Tool lifecycle statuses
ToolStatus = Literal[
    "generated",
    "validated",
    "eval_passed",
    "packaged",
    "published",
    "failed",
]


class ToolRegistry:
    """Load/save a flat JSON registry of tool specs with metadata."""

    def __init__(self, registry_path: Path) -> None:
        self._path = registry_path
        self._entries: dict[str, dict] = {}  # {slug: {spec, metadata}}
        if registry_path.exists():
            try:
                self._entries = json.loads(registry_path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, ValueError) as exc:
                logging.getLogger(__name__).warning(
                    "Registry file %s is corrupt or unreadable (%s); starting empty.", registry_path, exc
                )
                self._entries = {}

    # ------------------------------------------------------------------
    # Mutation
    # ------------------------------------------------------------------

    def register(self, spec: ToolSpec, status: ToolStatus = "generated") -> None:
        """Add or update a tool spec in the registry with initial metadata."""
        now = datetime.now(timezone.utc).isoformat()
        self._entries[spec.slug] = {
            "spec": json.loads(spec.model_dump_json()),
            "metadata": {
                "status": status,
                "registered_at": now,
                "updated_at": now,
                "eval_score": None,
                "last_run": None,
                "last_run_type": None,
                "last_run_success": None,
                "operational_last_run_success": None,
                "last_successful_run": None,
                "last_failed_run": None,
                "last_eval": None,
                "last_validation": None,
                "package_path": None,
                "mcp_path": None,
                "skill_path": None,
                "eval_path": None,
            },
        }
        self._save()

    def set_status(self, slug: str, status: ToolStatus) -> bool:
        """Update the status of a registered tool. Returns True if updated."""
        if slug not in self._entries:
            return False
        now = datetime.now(timezone.utc).isoformat()
        self._entries[slug]["metadata"]["status"] = status
        self._entries[slug]["metadata"]["status_updated_at"] = now
        self._entries[slug]["metadata"]["updated_at"] = now
        self._save()
        return True

    def set_eval_score(self, slug: str, score: float) -> bool:
        """Record an eval score for a tool."""
        if slug not in self._entries:
            return False
        now = datetime.now(timezone.utc).isoformat()
        self._entries[slug]["metadata"]["eval_score"] = score
        self._entries[slug]["metadata"]["last_eval"] = now
        self._entries[slug]["metadata"]["updated_at"] = now
        self._save()
        return True

    def set_validation_result(self, slug: str, valid: bool) -> bool:
        """Record validation result."""
        if slug not in self._entries:
            return False
        now = datetime.now(timezone.utc).isoformat()
        meta = self._entries[slug]["metadata"]
        meta["last_validation"] = now
        meta["validation_passed"] = valid
        meta["updated_at"] = now
        self._save()
        return True

    def set_last_run(
        self,
        slug: str,
        success: bool,
        run_type: str = "normal",
        operational_success: bool | None = None,
    ) -> bool:
        """Record runtime invocation timestamp and outcome."""
        if slug not in self._entries:
            return False
        now = datetime.now(timezone.utc).isoformat()
        meta = self._entries[slug]["metadata"]
        meta["last_run"] = now
        meta["last_run_type"] = run_type
        meta["last_run_success"] = success
        effective_operational = success if operational_success is None else operational_success
        meta["operational_last_run_success"] = effective_operational
        if success:
            meta["last_successful_run"] = now
        else:
            meta["last_failed_run"] = now
        meta["updated_at"] = now
        self._save()
        return True

    def set_package_path(self, slug: str, path: str | Path) -> bool:
        """Record the path to a packaged distribution."""
        if slug not in self._entries:
            return False
        now = datetime.now(timezone.utc).isoformat()
        self._entries[slug]["metadata"]["package_path"] = str(path)
        self._entries[slug]["metadata"]["updated_at"] = now
        self._save()
        return True

    def set_mcp_path(self, slug: str, path: str | Path) -> bool:
        """Record the path to an MCP server."""
        if slug not in self._entries:
            return False
        now = datetime.now(timezone.utc).isoformat()
        self._entries[slug]["metadata"]["mcp_path"] = str(path)
        self._entries[slug]["metadata"]["updated_at"] = now
        self._save()
        return True

    def set_skill_path(self, slug: str, path: str | Path) -> bool:
        """Record the path to a skill."""
        if slug not in self._entries:
            return False
        now = datetime.now(timezone.utc).isoformat()
        self._entries[slug]["metadata"]["skill_path"] = str(path)
        self._entries[slug]["metadata"]["updated_at"] = now
        self._save()
        return True

    def set_eval_path(self, slug: str, path: str | Path) -> bool:
        """Record the path to tool-local eval artifacts."""
        if slug not in self._entries:
            return False
        now = datetime.now(timezone.utc).isoformat()
        self._entries[slug]["metadata"]["eval_path"] = str(path)
        self._entries[slug]["metadata"]["updated_at"] = now
        self._save()
        return True

    def deregister(self, slug: str) -> bool:
        """Remove *slug* from the registry. Returns True if it existed."""
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
        spec_data = data.get("spec", data)  # Fallback for old format
        try:
            return ToolSpec.model_validate(spec_data)
        except ValidationError as exc:
            logging.getLogger(__name__).warning("Skipping corrupt spec for slug %r: %s", slug, exc)
            return None

    def get_metadata(self, slug: str) -> dict | None:
        """Return the metadata for a registered tool."""
        data = self._entries.get(slug)
        if data is None:
            return None
        return data.get("metadata", {})

    def list_all(self) -> list[ToolSpec]:
        """Return all registered tool specs."""
        specs = []
        for v in self._entries.values():
            spec_data = v["spec"] if "spec" in v else v  # Fallback for old format
            try:
                specs.append(ToolSpec.model_validate(spec_data))
            except ValidationError as exc:
                logging.getLogger(__name__).warning("Skipping corrupt entry in list_all: %s", exc)
        return specs

    def list_by_status(self, status: ToolStatus) -> list[ToolSpec]:
        """Return specs with a specific status."""
        specs = []
        for entry in self._entries.values():
            if entry.get("metadata", {}).get("status") == status:
                spec_data = entry["spec"] if "spec" in entry else entry
                try:
                    specs.append(ToolSpec.model_validate(spec_data))
                except ValidationError as exc:
                    logging.getLogger(__name__).warning("Skipping corrupt entry in list_by_status: %s", exc)
        return specs

    def search_by_tag(self, tag: str) -> list[ToolSpec]:
        """Return specs whose tags include *tag* (case-insensitive)."""
        tag_lower = tag.lower()
        specs = []
        for v in self._entries.values():
            spec_data = v["spec"] if "spec" in v else v
            if any(t.lower() == tag_lower for t in spec_data.get("tags", [])):
                try:
                    specs.append(ToolSpec.model_validate(spec_data))
                except ValidationError as exc:
                    logging.getLogger(__name__).warning("Skipping corrupt entry in search_by_tag: %s", exc)
        return specs

    def __iter__(self) -> Iterator[ToolSpec]:
        return iter(self.list_all())

    def __len__(self) -> int:
        return len(self._entries)

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        # Write to a sibling temp file then atomically rename so that a
        # mid-write crash or SIGKILL never leaves a truncated registry.
        fd, tmp_path = tempfile.mkstemp(
            dir=self._path.parent, prefix=".registry_tmp_", suffix=".json"
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                fh.write(json.dumps(self._entries, indent=2, default=str))
            os.replace(tmp_path, self._path)
        except Exception:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            raise
