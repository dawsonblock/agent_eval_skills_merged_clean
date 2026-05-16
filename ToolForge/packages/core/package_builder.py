"""
Package builder — bundles a generated tool into a distributable .zip archive.

Output: {dist_dir}/{slug}-{version}.zip

Archive layout:
  manifest.json           — spec + build metadata
  toolforge.yaml          — original spec file
  tool.py (or index.ts)   — entry point
  tests/                  — test suite
  mcp/                    — MCP server (if present)
  skills/                 — SKILL.md (if present)
  evals/                  — eval directory (if present)
"""
from __future__ import annotations

import hashlib
import json
import zipfile
from datetime import datetime, timezone
from pathlib import Path

from packages.core.tool_spec import ToolSpec


# Files/patterns to exclude from package
_EXCLUDE_PATTERNS = frozenset({
    ".env", ".env.local", ".env.*.local",
    "*.pem", "*.key", "*.p12", "*.pfx", "*.crt",
    "credentials*", "token*", "secret*", "password*",
    "__pycache__", ".pytest_cache", "node_modules",
    ".git", ".gitignore", ".DS_Store",
    "*.pyc", "*.pyo",
    "dist", "build", "*.egg-info",
    "runs", "logs", ".venv", "venv",
})

_EXCLUDE_SUFFIXES = frozenset({".pyc", ".pyo", ".env"})


def _should_exclude(file_path: Path) -> bool:
    """Check if a file should be excluded from the package."""
    name = file_path.name
    rel_path = str(file_path)
    
    # Check exact matches and wildcards
    if name in _EXCLUDE_PATTERNS:
        return True
    for pattern in _EXCLUDE_PATTERNS:
        if "*" in pattern:
            # Simple glob: e.g. "credentials*" matches "credentials.txt"
            prefix = pattern.replace("*", "")
            if name.startswith(prefix) or name.endswith(prefix):
                return True
        if pattern in rel_path:
            return True
    
    # Check suffixes
    if file_path.suffix in _EXCLUDE_SUFFIXES:
        return True
    
    return False


def build_package(
    spec: ToolSpec,
    tool_dir: Path,
    dist_dir: Path,
) -> Path:
    """
    Bundle *tool_dir* into *dist_dir/{slug}-{version}.zip*.
    Returns the path to the created archive.
    """
    dist_dir.mkdir(parents=True, exist_ok=True)
    archive_name = f"{spec.slug}-{spec.version}.zip"
    archive_path = dist_dir / archive_name

    # Build manifest with file list and SHA256 hashes
    manifest: dict = {
        "name": spec.name,
        "slug": spec.slug,
        "version": spec.version,
        "description": spec.description,
        "language": spec.language.value,
        "built_at": datetime.now(timezone.utc).isoformat(),
        "toolforge_version": "0.1.0",
        "tags": spec.tags,
        "author": spec.author,
        "files": [],
        "sha256": {},
    }

    with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        # Write manifest first (will update with file hashes before final write)
        temp_files: list[tuple[Path, str]] = []

        # Walk the tool directory and collect files
        for file_path in sorted(tool_dir.rglob("*")):
            if file_path.is_file():
                # Skip excluded files
                if _should_exclude(file_path):
                    continue

                arc_name = str(file_path.relative_to(tool_dir))
                
                # Compute SHA256
                sha256_hash = hashlib.sha256()
                with open(file_path, "rb") as f:
                    for chunk in iter(lambda: f.read(4096), b""):
                        sha256_hash.update(chunk)
                
                manifest["files"].append(arc_name)
                manifest["sha256"][arc_name] = sha256_hash.hexdigest()
                
                temp_files.append((file_path, arc_name))

        # Write manifest
        zf.writestr("manifest.json", json.dumps(manifest, indent=2))

        # Write all collected files
        for file_path, arc_name in temp_files:
            zf.write(file_path, arc_name)

    return archive_path
