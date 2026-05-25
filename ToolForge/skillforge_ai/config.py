from __future__ import annotations
# mypy: disable-error-code=import-untyped

from dataclasses import dataclass
from pathlib import Path

from skillforge_ai.schema_utils import validate_with_schema


@dataclass(frozen=True)
class SkillForgePaths:
    workspace_root: Path

    @property
    def repo_root(self) -> Path:
        return self.workspace_root

    @property
    def toolforge_root(self) -> Path:
        return self.workspace_root

    @property
    def skillforge_state_dir(self) -> Path:
        return self.runtime_root

    @property
    def runtime_root(self) -> Path:
        return self.workspace_root / ".skillforge"

    @property
    def registry_path(self) -> Path:
        return self.runtime_root / "registry.json"

    @property
    def tool_registry_path(self) -> Path:
        return self.runtime_root / "tool_registry.json"

    @property
    def permissions_path(self) -> Path:
        return self.runtime_root / "permissions.json"

    @property
    def runs_dir(self) -> Path:
        return self.runtime_root / "runs"

    @property
    def evidence_dir(self) -> Path:
        return self.runtime_root / "evidence"

    @property
    def packages_dir(self) -> Path:
        return self.runtime_root / "packages"

    @property
    def skills_dir(self) -> Path:
        return self.workspace_root / "skills"

    @property
    def generated_tools_dir(self) -> Path:
        return self.workspace_root / "tools" / "generated"


def ensure_runtime_state(workspace_root: Path) -> SkillForgePaths:
    paths = SkillForgePaths(workspace_root=workspace_root.resolve())
    paths.runtime_root.mkdir(parents=True, exist_ok=True)
    paths.runs_dir.mkdir(parents=True, exist_ok=True)
    paths.evidence_dir.mkdir(parents=True, exist_ok=True)
    paths.packages_dir.mkdir(parents=True, exist_ok=True)

    if not paths.registry_path.exists():
        paths.registry_path.write_text("[]\n", encoding="utf-8")
    if not paths.tool_registry_path.exists():
        paths.tool_registry_path.write_text("[]\n", encoding="utf-8")
    if not paths.permissions_path.exists():
        paths.permissions_path.write_text(
            (
                "{\n"
                '  "version": "0.1.0",\n'
                '  "default_mode": "interactive",\n'
                '  "rules": []\n'
                "}\n"
            ),
            encoding="utf-8",
        )

    _normalize_runtime_state(paths)

    return paths


def resolve_within_workspace(
    workspace_root: Path, path_value: Path | str
) -> Path:
    """Resolve a path and ensure it does not escape the provided workspace root."""
    root = workspace_root.resolve()
    candidate = Path(path_value)
    resolved = (
        candidate.resolve()
        if candidate.is_absolute()
        else (root / candidate).resolve()
    )
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise ValueError(f"Path escapes workspace root: {path_value}") from exc
    return resolved


def _normalize_runtime_state(paths: SkillForgePaths) -> None:
    import json

    registry_text = paths.registry_path.read_text(encoding="utf-8")
    tool_registry_text = paths.tool_registry_path.read_text(encoding="utf-8")
    permissions_text = paths.permissions_path.read_text(encoding="utf-8")

    try:
        registry_payload = json.loads(registry_text)
        validate_with_schema(registry_payload, "registry_schema.json")
    except Exception:
        paths.registry_path.write_text("[]\n", encoding="utf-8")

    try:
        tool_registry_payload = json.loads(tool_registry_text)
        if not isinstance(tool_registry_payload, list):
            raise ValueError("tool_registry.json must be a list")
        for item in tool_registry_payload:
            validate_with_schema(item, "tool_schema.json")
    except Exception:
        paths.tool_registry_path.write_text("[]\n", encoding="utf-8")

    try:
        permissions_payload = json.loads(permissions_text)
        validate_with_schema(permissions_payload, "permission_schema.json")
    except Exception:
        paths.permissions_path.write_text(
            (
                "{\n"
                '  "version": "0.1.0",\n'
                '  "default_mode": "interactive",\n'
                '  "rules": []\n'
                "}\n"
            ),
            encoding="utf-8",
        )
