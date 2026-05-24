from __future__ import annotations

import hashlib
import re
import zipfile
from pathlib import Path

from skillforge_ai.skill_registry import SkillRegistry
from skillforge_ai.tool_registry import SkillForgeRegistry


def run_install(workspace_root: Path, archive_path: Path) -> tuple[str, Path, str]:
    slug = _infer_slug(archive_path.stem)
    dest = workspace_root / "tools" / "generated" / slug
    dest.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive_path) as zf:
        zf.extractall(dest)

    sha256 = _sha256(archive_path)

    skill_reg = SkillRegistry(workspace_root)
    entry = skill_reg.get(slug) or {"name": slug}
    entry.update(
        {
            "installed_from": str(archive_path),
            "installed_hash": sha256,
            "status": "installed",
            "path": str(dest),
        }
    )
    skill_reg.upsert(entry)

    tool_entry = {
        "name": f"{slug}_tool",
        "type": "python",
        "entrypoint": str(dest / "tool.py"),
        "description": f"Installed tool for {slug}",
        "permissions": ["read_files", "write_files"],
        "risk_level": "low",
        "validated": False,
        "mcp_server": str(dest / "mcp" / "server.py")
        if (dest / "mcp" / "server.py").exists()
        else None,
    }
    SkillForgeRegistry(workspace_root).register_tool(tool_entry)
    return slug, dest, sha256


def _infer_slug(stem: str) -> str:
    version_or_ts = re.compile(
        r"^(?P<slug>.+?)-(?:(?:v)?\d+\.\d+\.\d+(?:[-._A-Za-z0-9]*)|\d{8}_\d{6})$"
    )
    match = version_or_ts.match(stem)
    if match:
        return match.group("slug")
    return stem


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()
