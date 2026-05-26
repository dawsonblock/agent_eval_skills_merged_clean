#!/usr/bin/env python3
from __future__ import annotations

import fnmatch
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "RELEASE_MANIFEST.json"

EXCLUDED_PATTERNS = [
    "*/__pycache__/*",
    "*.pyc",
    "*.pyo",
    "*/node_modules/*",
    "*/.venv/*",
    "*/.git/*",
    "*/.DS_Store",
    "*/dist/*",
    "*/withdrawn/*",
]

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


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def should_include(path: Path) -> bool:
    rel = path.relative_to(ROOT)
    rel_s = rel.as_posix()

    top = rel.parts[0]
    if top not in INCLUDED_TOP_LEVEL:
        return False

    for pattern in EXCLUDED_PATTERNS:
        if fnmatch.fnmatch(rel_s, pattern) or fnmatch.fnmatch(f"{rel_s}/", pattern):
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
    "excluded_patterns": EXCLUDED_PATTERNS,
}

OUT.write_text(json.dumps(manifest, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
print(f"Wrote {OUT}")
