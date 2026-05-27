#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "RELEASE_MANIFEST.json"

EXCLUDED_PARTS = {
    ".git",
    ".venv",
    "node_modules",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".skillforge",
    ".validation_logs",
    "dist",
    "withdrawn",
    "__MACOSX",
    "outputs",
}

EXCLUDED_PREFIXES = ("._",)
EXCLUDED_NAMES = {".DS_Store"}
EXCLUDED_SUFFIXES = {".pyc", ".pyo"}

INCLUDED_TOP_LEVEL = {
    "ToolForge",
    "agent-skills-curated",
    "toolathlon-gym-curated",
    "scripts",
    "release_artifacts",
    "README.md",
    "RELEASE_STATUS.json",
    "CLAIMS_MATRIX.md",
}

EXCLUDED_RELATIVE_PATHS = {
    "toolathlon-gym-curated/configs/mcp_servers/google_calendar.yaml",
}

EXCLUDED_RELATIVE_PREFIXES = (
    "toolathlon-gym-curated/local_servers/Calendar-Autoauth-MCP-Server/build/",
)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def should_include(path: Path) -> bool:
    rel = path.relative_to(ROOT)
    rel_posix = rel.as_posix()

    top = rel.parts[0]
    if top not in INCLUDED_TOP_LEVEL:
        return False

    if rel_posix in EXCLUDED_RELATIVE_PATHS:
        return False

    if any(rel_posix.startswith(prefix) for prefix in EXCLUDED_RELATIVE_PREFIXES):
        return False

    if any(part in EXCLUDED_PARTS for part in rel.parts):
        return False

    if path.name in EXCLUDED_NAMES:
        return False

    if path.suffix in EXCLUDED_SUFFIXES:
        return False

    if any(path.name.startswith(prefix) for prefix in EXCLUDED_PREFIXES):
        return False

    # Treat runtime tool outputs as forbidden release-manifest entries.
    if "tool" in rel.parts and "outputs" in rel.parts:
        return False

    return path.is_file()


files = []
for p in sorted(ROOT.rglob("*")):
    if should_include(p):
        files.append({"path": p.relative_to(ROOT).as_posix(), "sha256": sha256(p)})

manifest = {
    "release_name": "agent_eval_skills_merged_clean-pruned-smoke",
    "created_at_utc": datetime.now(timezone.utc).isoformat(),
    "profile": "smoke",
    "files": files,
    "excluded_parts": sorted(EXCLUDED_PARTS),
    "excluded_prefixes": list(EXCLUDED_PREFIXES),
    "excluded_names": sorted(EXCLUDED_NAMES),
    "excluded_suffixes": sorted(EXCLUDED_SUFFIXES),
}

OUT.write_text(json.dumps(manifest, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
print(f"Wrote {OUT}")
