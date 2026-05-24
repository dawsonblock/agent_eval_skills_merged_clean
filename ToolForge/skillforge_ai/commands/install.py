from __future__ import annotations

import zipfile
from pathlib import Path


def run_install(workspace_root: Path, archive_path: Path) -> tuple[str, Path]:
    slug = archive_path.stem.split("-")[0]
    dest = workspace_root / "tools" / "generated" / slug
    dest.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive_path) as zf:
        zf.extractall(dest)
    return slug, dest
