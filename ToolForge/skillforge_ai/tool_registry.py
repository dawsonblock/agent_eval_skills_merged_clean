"""
SkillForgeRegistry — SkillForge-schema adapter over ToolForge's ToolRegistry.

Maps ToolForge's ``ToolStatus`` lifecycle to SkillForge concepts:

  ToolForge status   → SkillForge validated
  ──────────────────────────────────────────
  generated          → False
  validated          → True
  eval_passed        → True
  packaged           → True
  published          → True
  failed             → False (with error note)

Usage::

    reg = SkillForgeRegistry(workspace_root=Path("."))
    reg.register_skill(manifest, tool_dir)
    skills = reg.list_skills()
    reg.mark_validated("csv-cleaner")
"""
# mypy: disable-error-code=import-untyped

from __future__ import annotations

import logging
import json
import sys
from pathlib import Path
from typing import Any

from skillforge_ai.config import ensure_runtime_state
from skillforge_ai.models import SkillManifest
from skillforge_ai.schema_utils import validate_with_schema

logger = logging.getLogger(__name__)

_VALIDATED_STATUSES = frozenset(
    {"validated", "eval_passed", "packaged", "published"}
)


def _add_packages_to_path(workspace_root: Path) -> None:
    pkg_root = str(workspace_root)
    if pkg_root not in sys.path:
        sys.path.insert(0, pkg_root)


class SkillForgeRegistry:
    """
    SkillForge-layer view of the ToolForge ToolRegistry.

    Provides a simplified interface focused on SkillForge concepts (skills,
    risk levels, MCP servers) while delegating persistence to ToolRegistry.
    """

    def __init__(self, workspace_root: Path) -> None:
        self._root = workspace_root.resolve()
        self._registry_path = self._root / "toolforge_registry.json"
        self._paths = ensure_runtime_state(self._root)
        self._tool_registry_path = self._paths.tool_registry_path
        _add_packages_to_path(self._root)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def register_skill(
        self,
        manifest: SkillManifest,
        tool_dir: Path,
    ) -> None:
        """
        Register or update *manifest* in the underlying ToolRegistry.

        Tries to load the ToolSpec from toolforge.yaml if it exists so that
        ToolRegistry can store the full spec.  Falls back to a synthetic
        registration if the spec file is missing.
        """
        registry = self._get_registry()
        yaml_path = tool_dir / "toolforge.yaml"
        if yaml_path.exists():
            spec = self._load_spec(yaml_path)
            if spec is not None:
                try:
                    registry.register(spec, status="generated")
                    return
                except Exception as exc:
                    logger.debug(
                        "registry.register(spec) failed: %s "
                        "— using raw register",
                        exc,
                    )

        # Synthetic fallback: patch the registry JSON directly
        self._register_raw(manifest, tool_dir)

    def get_skill(self, name: str) -> dict[str, Any] | None:
        """Return the SkillForge-schema view of a skill, or None."""
        registry = self._get_registry()
        try:
            entry = registry.find(name)
            metadata = registry.get_metadata(name)
        except Exception:
            return None
        if entry is None:
            return None
        return self._to_skill_dict(entry, metadata)

    def list_skills(self) -> list[dict[str, Any]]:
        """List all registered skills in SkillForge format."""
        registry = self._get_registry()
        try:
            all_entries = registry.list_all()
        except Exception as exc:
            logger.warning("registry.list_all() failed: %s", exc)
            return []
        out: list[dict[str, Any]] = []
        for entry in all_entries:
            slug = getattr(entry, "slug", None)
            if slug is None and isinstance(entry, dict):
                slug = entry.get("slug") or entry.get("name")
            metadata = registry.get_metadata(slug) if slug else None
            out.append(self._to_skill_dict(entry, metadata))
        return out

    def list_tools(self) -> list[dict[str, Any]]:
        """Alias for list_skills() — returns the same list."""
        return self.list_skills()

    def mark_validated(self, name: str) -> None:
        """Promote a skill to *validated* status."""
        self._set_status(name, "validated")

    def mark_failed(self, name: str, error: str = "") -> None:
        """Mark a skill as *failed* and optionally record the error."""
        self._set_status(name, "failed")
        if error:
            registry = self._get_registry()
            try:
                registry.set_validation_result(name, False)
            except Exception as exc:
                logger.debug("set_validation_result failed: %s", exc)

    def mark_packaged(self, name: str) -> None:
        """Promote a skill to *packaged* status."""
        self._set_status(name, "packaged")

    def mark_tool_validated(self, name: str, validated: bool) -> None:
        """Update the validated flag for a registered callable tool."""
        data = self._read_tool_registry()
        out: list[dict[str, Any]] = []
        updated = False
        for item in data:
            if item.get("name") == name:
                normalized = dict(item)
                normalized["validated"] = validated
                out.append(normalized)
                updated = True
            else:
                out.append(item)
        if updated:
            self._write_tool_registry(out)

    def register_tool(self, tool_entry: dict[str, Any]) -> None:
        """Register a callable tool in the local SkillForge tool registry."""
        entrypoint = str(tool_entry.get("entrypoint", "")).strip()
        working_dir = str(tool_entry.get("working_dir", "")).strip()
        if not working_dir and entrypoint:
            working_dir = str(Path(entrypoint).parent)

        normalized_entry = {
            "name": str(tool_entry.get("name", "")).strip(),
            "type": str(tool_entry.get("type", "python")).strip() or "python",
            "entrypoint": entrypoint,
            "working_dir": working_dir,
            "description": (
                str(tool_entry.get("description", "Registered tool")).strip()
                or "Registered tool"
            ),
            "permissions": tool_entry.get("permissions", []),
            "risk_level": (
                str(tool_entry.get("risk_level", "low")).strip() or "low"
            ),
            "validated": bool(tool_entry.get("validated", False)),
            "mcp_server": tool_entry.get("mcp_server"),
        }

        validate_with_schema(normalized_entry, "tool_schema.json")

        data = self._read_tool_registry()
        out: list[dict[str, Any]] = []
        replaced = False
        name = normalized_entry["name"]
        for item in data:
            if item.get("name") == name:
                out.append(normalized_entry)
                replaced = True
            else:
                out.append(item)
        if not replaced:
            out.append(normalized_entry)
        self._write_tool_registry(out)

    def get_registered_tool(self, name: str) -> dict[str, Any] | None:
        """Lookup a callable tool by name from local tool registry."""
        for item in self._read_tool_registry():
            if item.get("name") == name:
                return item
        return None

    def list_registered_tools(self) -> list[dict[str, Any]]:
        """Return callable tools from local SkillForge tool registry."""
        return self._read_tool_registry()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _get_registry(self) -> Any:
        from packages.core.registry import ToolRegistry

        return ToolRegistry(self._registry_path)

    def _load_spec(self, yaml_path: Path) -> Any | None:
        try:
            from packages.validators.schema_validator import validate_yaml_file

            return validate_yaml_file(yaml_path)
        except Exception as exc:
            logger.debug("Could not load spec from %s: %s", yaml_path, exc)
            return None

    def _register_raw(self, manifest: SkillManifest, tool_dir: Path) -> None:
        """
        Write a minimal registry entry directly to the JSON file when we
        cannot load a full ToolSpec.

        Writes in ToolRegistry-compatible format:
            { "<slug>": { "spec": {...}, "metadata": {...} }, ... }
        """
        import json
        from datetime import datetime, timezone

        now = datetime.now(timezone.utc).isoformat()

        # Load existing registry (flat slug→entry dict)
        data: dict[str, Any] = {}
        if self._registry_path.exists():
            try:
                with self._registry_path.open() as fh:
                    data = json.load(fh)
            except Exception:
                data = {}

        # Write entry in ToolRegistry-expected format
        data[manifest.name] = {
            "spec": {
                "name": manifest.name,
                "slug": manifest.name,
                "description": manifest.description,
            },
            "metadata": {
                "status": "generated",
                "registered_at": now,
                "updated_at": now,
                "category": manifest.category,
                "risk_level": manifest.risk_level,
                "mcp_servers": manifest.mcp_servers,
                "permissions": manifest.permissions,
                "tool_dir": str(tool_dir),
            },
        }

        self._registry_path.parent.mkdir(parents=True, exist_ok=True)
        with self._registry_path.open("w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2)

    def _set_status(self, name: str, status: str) -> None:
        registry = self._get_registry()
        try:
            registry.set_status(name, status)
        except Exception as exc:
            logger.warning("set_status(%s, %s) failed: %s", name, status, exc)

    def _read_tool_registry(self) -> list[dict[str, Any]]:
        try:
            payload = json.loads(
                self._tool_registry_path.read_text(encoding="utf-8")
            )
        except Exception:
            return []
        if not isinstance(payload, list):
            return []
        try:
            for item in payload:
                validate_with_schema(item, "tool_schema.json")
        except Exception:
            return []
        return payload

    def _write_tool_registry(self, data: list[dict[str, Any]]) -> None:
        for item in data:
            validate_with_schema(item, "tool_schema.json")
        self._tool_registry_path.write_text(
            json.dumps(data, indent=2) + "\n",
            encoding="utf-8",
        )

    def _to_skill_dict(
        self,
        entry: Any,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Convert a ToolRegistry entry to SkillForge format."""
        # registry.list_all() can return dicts or objects
        if hasattr(entry, "__dict__"):
            d = entry.__dict__
        elif isinstance(entry, dict):
            d = entry
        else:
            d = {}
        meta = metadata or {}

        slug = d.get("slug", d.get("name", "unknown"))
        status = str(meta.get("status", d.get("status", "generated")))

        # Infer MCP server path
        mcp_server: str | None = None
        tool_dir = meta.get("tool_dir", d.get("tool_dir"))
        if tool_dir:
            mcp_path = Path(tool_dir) / "mcp" / "server.py"
            if mcp_path.exists():
                mcp_server = str(mcp_path)

        return {
            "name": slug,
            "type": "skill",
            "description": d.get("description", ""),
            "entrypoint": d.get(
                "entry_point",
                d.get("entrypoint", f"tools/generated/{slug}/tool.py"),
            ),
            "permissions": meta.get("permissions", d.get("permissions", [])),
            "risk_level": meta.get("risk_level", d.get("risk_level", "low")),
            "validated": status in _VALIDATED_STATUSES,
            "mcp_server": mcp_server,
            "status": status,
            "category": meta.get("category", d.get("category", "generated")),
        }
