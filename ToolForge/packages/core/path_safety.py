"""
Path safety validator for tool inputs.

This module enforces tool-local filesystem boundaries before tool execution.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

from packages.core.tool_spec import SecuritySpec


class PathViolationError(Exception):
    """Raised when a path violates security constraints."""


_READ_KEYS = {
    "input_path",
    "input_file",
    "source_path",
    "source_file",
    "read_path",
    "file_path",
    "path",
    "input_dir",
    "directory",
    "folder",
}

_WRITE_KEYS = {
    "output_path",
    "output_file",
    "dest_path",
    "destination_path",
    "target_path",
    "output_dir",
}


def _expand_pattern(pattern: str, workspace: Path) -> Path:
    expanded = Path(pattern).expanduser()
    if expanded.is_absolute():
        return expanded.resolve(strict=False)
    cleaned = pattern
    if cleaned.startswith("./"):
        cleaned = cleaned[2:]
    if cleaned.endswith("/**"):
        cleaned = cleaned[:-3]
    if cleaned.endswith("/*"):
        cleaned = cleaned[:-2]
    return (workspace / cleaned).resolve(strict=False)


def _resolve_input_path(value: str, workspace: Path) -> Path:
    candidate = Path(value).expanduser()
    if candidate.is_absolute():
        return candidate.resolve(strict=False)
    return (workspace / candidate).resolve(strict=False)


def _is_within(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def _matches_any(path: Path, patterns: list[str], workspace: Path) -> bool:
    for pattern in patterns:
        root = _expand_pattern(pattern, workspace)
        if _is_within(path, root):
            return True
    return False


def is_path_like_key(key: str) -> bool:
    lowered = key.strip().lower()
    return lowered in _READ_KEYS or lowered in _WRITE_KEYS or lowered.endswith(
        ("_path", "_file", "_dir", "_directory", "_folder")
    )


def classify_path_mode(key: str) -> Literal["read", "write", "unknown"]:
    lowered = key.strip().lower()
    if lowered.startswith(("input_", "source_", "read_")):
        return "read"
    if lowered == "file_path":
        return "read"
    if lowered in {"input_dir", "directory", "folder"}:
        return "read"
    if lowered.startswith(("output_", "dest_", "destination_", "target_")):
        return "write"
    if lowered == "output_dir":
        return "write"
    if lowered == "path":
        return "read"
    return "unknown"


def _enforce_blocked(path: Path, security: SecuritySpec, workspace: Path) -> None:
    if security.blocked_paths and _matches_any(path, security.blocked_paths, workspace):
        raise PathViolationError(
            f"Resolved path '{path}' matches blocked_paths policy"
        )


def _enforce_extensions(path: Path, security: SecuritySpec) -> None:
    if not security.allowed_extensions:
        return
    if path.suffix.lower() not in {ext.lower() for ext in security.allowed_extensions}:
        raise PathViolationError(
            f"Extension '{path.suffix}' is not allowed; allowed_extensions={security.allowed_extensions}"
        )


def _enforce_symlink(path: Path, security: SecuritySpec) -> None:
    if security.allow_symlinks:
        return
    if path.exists() and path.is_symlink():
        raise PathViolationError("Symlink inputs are not allowed")


def _enforce_max_size(path: Path, security: SecuritySpec) -> None:
    if not path.exists() or not path.is_file():
        return
    max_bytes = security.max_file_size_mb * 1024 * 1024
    if path.stat().st_size > max_bytes:
        raise PathViolationError(
            f"File exceeds max_file_size_mb={security.max_file_size_mb}"
        )


def _allowed_roots(
    mode: Literal["read", "write"],
    security: SecuritySpec,
) -> list[str]:
    if mode == "read":
        return list(security.allowed_read_paths)
    return list(security.allowed_write_paths)


def validate_path_input(
    key: str,
    value: Any,
    security: SecuritySpec,
    workspace: Path,
) -> None:
    if not is_path_like_key(key):
        return
    if not isinstance(value, str) or not value.strip():
        raise PathViolationError(f"Path input '{key}' must be a non-empty string")
    if not security.requires_filesystem:
        raise PathViolationError(
            f"Path input '{key}' is not allowed when requires_filesystem is false"
        )

    workspace_root = workspace.resolve(strict=False)
    raw_candidate = Path(value).expanduser()
    raw_workspace_path = (
        raw_candidate
        if raw_candidate.is_absolute()
        else workspace_root / raw_candidate
    )
    raw_resolved = (
        raw_candidate.resolve(strict=False)
        if raw_candidate.is_absolute()
        else (workspace_root / raw_candidate).resolve(strict=False)
    )
    if (
        not security.allow_symlinks
        and raw_workspace_path.exists()
        and raw_workspace_path.is_symlink()
    ):
        raise PathViolationError("Symlink inputs are not allowed")
    if not security.allow_symlinks and raw_resolved.exists() and raw_resolved.is_symlink():
        raise PathViolationError("Symlink inputs are not allowed")

    resolved = _resolve_input_path(value, workspace_root)
    mode = classify_path_mode(key)

    _enforce_blocked(resolved, security, workspace_root)
    _enforce_symlink(resolved, security)

    if mode == "unknown":
        raise PathViolationError(f"Unable to classify path mode for '{key}'")

    roots = _allowed_roots(mode, security)
    if not roots:
        raise PathViolationError(
            f"No allowed {mode} paths configured for filesystem access"
        )

    if mode == "read":
        if not _matches_any(resolved, roots, workspace_root):
            raise PathViolationError(
                f"Read path '{value}' resolved outside allowed_read_paths"
            )
        _enforce_extensions(resolved, security)
        _enforce_max_size(resolved, security)
        if not resolved.exists():
            raise PathViolationError(f"Input file not found: {value}")

    if mode == "write":
        parent = resolved.parent.resolve(strict=False)
        if not _matches_any(parent, roots, workspace_root):
            raise PathViolationError(
                f"Write path '{value}' resolved outside allowed_write_paths"
            )
        _enforce_extensions(resolved, security)


def validate_all_path_inputs(
    inputs: dict[str, Any],
    security: SecuritySpec,
    workspace: Path,
) -> None:
    for key, value in inputs.items():
        if is_path_like_key(key):
            validate_path_input(key, value, security, workspace)
