from __future__ import annotations

import datetime
import zipfile
from pathlib import Path

from skillforge_ai.tool_registry import SkillForgeRegistry


def run_package(
    workspace_root: Path,
    slug: str,
    output: Path | None,
) -> Path:
    tool_dir = workspace_root / "tools" / "generated" / slug
    if not tool_dir.exists():
        raise FileNotFoundError(f"Tool directory not found for '{slug}'")

    out_dir = workspace_root / "dist"
    out_dir.mkdir(exist_ok=True)

    if output is None:
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        output = out_dir / f"{slug}-{ts}.zip"

    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as zf:
        for file_path in tool_dir.rglob("*"):
            if file_path.is_file():
                zf.write(file_path, file_path.relative_to(tool_dir))

    SkillForgeRegistry(workspace_root).mark_packaged(slug)
    return output
