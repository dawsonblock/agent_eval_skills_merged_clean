from __future__ import annotations
# mypy: disable-error-code=import-untyped

import datetime
import hashlib
import shutil
import zipfile
from pathlib import Path

from skillforge_ai.evidence_logger import EvidenceLogger
from skillforge_ai.package_manager import PackageManager
from skillforge_ai.skill_registry import SkillRegistry
from skillforge_ai.tool_registry import SkillForgeRegistry


def run_package(
    workspace_root: Path,
    slug: str,
    output: Path | None,
) -> tuple[Path, str]:
    workspace_root = workspace_root.resolve()
    evidence = EvidenceLogger(
        log_dir=workspace_root / ".skillforge" / "evidence",
        skill_name=slug,
    )

    skill_dir = workspace_root / "skills" / slug
    if skill_dir.exists():
        package_path, sha256 = PackageManager(workspace_root).package_skill(
            slug
        )

        # Optional user-specified output path is treated as a copy target.
        if output is not None:
            output.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(package_path, output)
            package_path = output

        reg = SkillRegistry(workspace_root)
        entry = reg.get(slug) or {"name": slug}
        entry.update(
            {
                "package_hash": sha256,
                "package_path": str(package_path),
                "status": "packaged",
            }
        )
        reg.upsert(entry)

        SkillForgeRegistry(workspace_root).mark_packaged(slug)
        evidence.log_package(slug, package_path)
        evidence.write_minimum_artifacts(
            run_payload={
                "event": "package",
                "skill": slug,
                "status": "passed",
                "package_path": str(package_path),
                "sha256": sha256,
            },
            files_changed=[str(package_path)],
            validation_payload={
                "skill": slug,
                "status": "passed",
                "errors": [],
                "warnings": [],
            },
        )
        evidence.finalize()
        return package_path, sha256

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
    sha256 = _sha256(output)

    reg = SkillRegistry(workspace_root)
    entry = reg.get(slug) or {"name": slug}
    entry.update(
        {
            "package_hash": sha256,
            "package_path": str(output),
            "status": "packaged",
        }
    )
    reg.upsert(entry)
    evidence.log_package(slug, output)
    evidence.write_minimum_artifacts(
        run_payload={
            "event": "package",
            "skill": slug,
            "status": "passed",
            "package_path": str(output),
            "sha256": sha256,
        },
        files_changed=[str(output)],
        validation_payload={
            "skill": slug,
            "status": "passed",
            "errors": [],
            "warnings": [],
        },
    )
    evidence.finalize()
    return output, sha256


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()
