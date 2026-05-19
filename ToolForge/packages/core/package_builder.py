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

import fnmatch
import hashlib
import json
import os
import zipfile
from datetime import datetime, timezone
from pathlib import Path

from packages.core.tool_spec import ToolLanguage, ToolSpec


# Files/patterns to exclude from package
_EXCLUDE_PATTERNS = frozenset({
    ".coverage",
    ".pytest_report.json",
    ".env", ".env.local", ".env.*.local",
    "*.pem", "*.key", "*.p12", "*.pfx", "*.crt",
    "credentials*", "token*", "secret*", "password*",
    "__pycache__", ".pytest_cache", "node_modules",
    ".git", ".gitignore", ".DS_Store",
    "*.pyc", "*.pyo",
    "dist", "build", "*.egg-info",
    "runs", "logs", "outputs", "htmlcov", ".venv", "venv",
})

_EXCLUDE_SUFFIXES = frozenset({".pyc", ".pyo", ".env"})


def _should_exclude(file_path: Path) -> bool:
    """Check if a file should be excluded from the package."""
    name = file_path.name
    rel_path = str(file_path)

    # Check exact matches and wildcards
    if name in _EXCLUDE_PATTERNS:
        return True
    path_parts = set(Path(rel_path).parts)
    for pattern in _EXCLUDE_PATTERNS:
        if "*" in pattern:
            if fnmatch.fnmatch(name, pattern):
                return True
        elif "/" not in pattern:
            # Non-wildcard, non-path patterns must match a whole path component
            # to avoid false positives (e.g. "outputs" must not match
            # "expected_outputs" as a substring).
            if pattern in path_parts:
                return True
        else:
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

    # Ensure SECURITY.md exists for packaged artifacts.
    security_md = tool_dir / "SECURITY.md"
    if not security_md.exists():
        security_md.write_text(
            "\n".join(
                [
                    f"# Security Notes: {spec.name}",
                    "",
                    "## Declared Permissions",
                    f"- requires_filesystem: {spec.security.requires_filesystem}",
                    f"- requires_network: {spec.security.requires_network}",
                    f"- requires_shell: {spec.security.requires_shell}",
                    "",
                    "## Filesystem Restrictions",
                    f"- allowed_read_paths: {spec.security.allowed_read_paths}",
                    f"- allowed_write_paths: {spec.security.allowed_write_paths}",
                    f"- blocked_paths: {spec.security.blocked_paths}",
                    "",
                    "## Network Restrictions",
                    f"- allowed_domains: {spec.security.allowed_domains}",
                    f"- blocked_domains: {spec.security.blocked_domains}",
                    "",
                    "## Shell Restrictions",
                    f"- allowed_commands: {spec.security.allowed_commands}",
                    f"- blocked_commands: {spec.security.blocked_commands}",
                    "",
                    "## Sandbox",
                    f"- sandbox_level: {spec.sandbox_level}",
                    "",
                    "## Known Limitations",
                    "- Generated tools require human review before sensitive use.",
                    "- Path safety and static checks reduce risk but are not a full security audit.",
                    "",
                    "## Review Warning",
                    "- Do not treat this package as production-ready without additional hardening.",
                ]
            ),
            encoding="utf-8",
        )

    required_files = [
        tool_dir / "toolforge.yaml",
        tool_dir / spec.entry_point,
        tool_dir / "README.md",
        tool_dir / "SECURITY.md",
    ]
    required_dirs = [
        tool_dir / "examples",
        tool_dir / "tests",
        tool_dir / "mcp",
        tool_dir / "skill",
        tool_dir / "evals",
    ]
    missing: list[str] = []
    for required in required_files:
        if not required.exists():
            missing.append(str(required.relative_to(tool_dir)))
    for required in required_dirs:
        if not required.exists() or not required.is_dir():
            missing.append(str(required.relative_to(tool_dir)) + "/")

    mcp_entry = (
        tool_dir / "mcp" / "src" / "index.ts"
        if spec.mcp.server_language == ToolLanguage.TYPESCRIPT
        else tool_dir / "mcp" / "server.py"
    )

    required_nested_files = [
        mcp_entry,
        tool_dir / "skill" / "SKILL.md",
        tool_dir / "evals" / "task_config.json",
    ]
    for required in required_nested_files:
        if not required.exists() or not required.is_file():
            missing.append(str(required.relative_to(tool_dir)))

    eval_case_files = list((tool_dir / "evals" / "cases").glob("*.json"))
    if not eval_case_files:
        missing.append("evals/cases/*.json")
    if missing:
        missing_list = ", ".join(sorted(missing))
        raise FileNotFoundError(
            "Cannot package tool; required artifacts are missing: "
            + missing_list
        )

    # Build manifest with file list and SHA256 hashes
    manifest: dict = {
        "name": spec.name,
        "slug": spec.slug,
        "version": spec.version,
        "description": spec.description,
        "language": spec.language.value,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "toolforge_version": "0.1.0",
        "tags": spec.tags,
        "author": spec.author,
        "validation_status": "unknown",
        "eval_status": "unknown",
        "files": [],
        "sha256": {},
    }

    with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        # Write manifest first (will update with file hashes before final write)
        temp_files: list[tuple[Path, str]] = []

        # Walk the tool directory and collect files.
        # os.walk with followlinks=False prevents symlink cycles and avoids
        # following links that might point outside the tool directory.
        # Excluded directories are pruned in-place so we never descend into
        # __pycache__, dist, node_modules, etc.
        for dirpath_str, dirnames, filenames in os.walk(tool_dir, followlinks=False):
            dirpath = Path(dirpath_str)
            # Prune excluded directories before descending (sorted for
            # deterministic archive ordering).
            dirnames[:] = sorted(
                d for d in dirnames if not _should_exclude(dirpath / d)
            )
            for filename in sorted(filenames):
                file_path = dirpath / filename
                # Skip symlinks and excluded files
                if file_path.is_symlink() or _should_exclude(file_path):
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
