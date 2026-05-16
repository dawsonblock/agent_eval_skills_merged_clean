"""
Path safety validator — prevents path traversal and unsafe filesystem access.

Ensures that tool inputs referencing files stay within allowed prefixes.
Blocks: ../, ~/, absolute paths, symlink escapes.
"""
from __future__ import annotations

from pathlib import Path


class PathViolationError(Exception):
    """Raised when a path violates security constraints."""

    pass


def normalize_path(path: str) -> Path:
    """
    Normalize a path: resolve .., ~, symlinks, and make absolute.

    Examples:
      "examples/input.csv" → /full/path/to/examples/input.csv
      "../../../etc/passwd" → /etc/passwd (reveals the escape attempt)
      "~/secret" → /Users/username/secret
    """
    p = Path(path).expanduser()
    try:
        # Resolve all symlinks and normalize
        resolved = p.resolve()
        return resolved
    except (RuntimeError, OSError) as e:
        # If resolve fails (e.g., path doesn't exist yet), fall back to normalization
        # This is needed for paths we're about to create
        if p.is_absolute():
            return p
        # Relative path: resolve against cwd
        return Path.cwd() / p


def is_path_safe(
    path: str,
    allowed_prefixes: list[str] | None = None,
    work_dir: str | None = None,
) -> bool:
    """
    Check if *path* is safe to access given *allowed_prefixes*.

    Args:
        path: The path to validate (e.g., "inputs/data.csv" or "../../../etc/passwd")
        allowed_prefixes: List of glob patterns or absolute paths. If None, uses work_dir only.
        work_dir: The root directory for relative paths (default: cwd).

    Returns:
        True if path is safe, False otherwise.

    Raises:
        PathViolationError: If path clearly violates constraints.
    """
    work = Path(work_dir or Path.cwd())
    resolved = normalize_path(path)

    # If no allowed prefixes given, only allow within work_dir
    if allowed_prefixes is None:
        try:
            resolved.relative_to(work)
            return True
        except ValueError:
            return False

    # Check against each allowed prefix
    for prefix_pattern in allowed_prefixes:
        # Handle glob patterns: "examples/**"
        if "**" in prefix_pattern:
            prefix_base = prefix_pattern.rstrip("/**")
            prefix_path = normalize_path(prefix_base) if not Path(prefix_base).is_absolute() else Path(prefix_base).resolve()
            try:
                resolved.relative_to(prefix_path)
                return True
            except ValueError:
                continue
        else:
            # Exact prefix match
            prefix_path = normalize_path(prefix_pattern) if not Path(prefix_pattern).is_absolute() else Path(prefix_pattern).resolve()
            if str(resolved).startswith(str(prefix_path)):
                return True

    return False


def validate_path(
    path: str,
    allowed_prefixes: list[str] | None = None,
    work_dir: str | None = None,
) -> Path:
    """
    Validate a path against allowed prefixes. Raise if unsafe.

    Args:
        path: The path to validate.
        allowed_prefixes: List of allowed base paths or glob patterns.
        work_dir: The root directory for relative paths (default: cwd).

    Returns:
        The resolved Path object if valid.

    Raises:
        PathViolationError: If path is outside allowed prefixes.
    """
    if not is_path_safe(path, allowed_prefixes, work_dir):
        resolved = normalize_path(path)
        raise PathViolationError(
            f"Path '{path}' (resolved to '{resolved}') is outside allowed prefixes: {allowed_prefixes}"
        )
    return normalize_path(path)


# Convenience validators for common cases
def validate_read_path(
    path: str,
    allowed_read_paths: list[str] | None = None,
    work_dir: str | None = None,
) -> Path:
    """Validate a path for reading."""
    return validate_path(path, allowed_read_paths or ["./"], work_dir)


def validate_write_path(
    path: str,
    allowed_write_paths: list[str] | None = None,
    work_dir: str | None = None,
) -> Path:
    """Validate a path for writing."""
    return validate_path(path, allowed_write_paths or ["./outputs"], work_dir)
