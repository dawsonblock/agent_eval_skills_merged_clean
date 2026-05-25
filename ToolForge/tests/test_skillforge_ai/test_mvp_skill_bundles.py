from __future__ import annotations

import json
import shutil
from importlib import util as importlib_util
from pathlib import Path

from skillforge_ai.commands.package import run_package


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _copy_skill_to_tmp(tmp_path: Path, slug: str) -> Path:
    src = _repo_root() / "skills" / slug
    dest = tmp_path / "skills" / slug
    shutil.copytree(src, dest)
    return dest


def _load_run_func(skill_dir: Path, module_name: str):
    module_path = skill_dir / "tool" / "main.py"
    spec = importlib_util.spec_from_file_location(module_name, module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load module at {module_path}")
    module = importlib_util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.run


def test_pdf_to_markdown_smoke(tmp_path: Path):
    source_dir = _copy_skill_to_tmp(tmp_path, "pdf-to-markdown")
    run = _load_run_func(source_dir, "pdf_to_markdown_main")

    pdf_file = tmp_path / "example.pdf"
    out_file = tmp_path / "example.md"
    pdf_file.write_bytes(
        b"%PDF-1.4\\nstream\\nRoadmap milestone details\\nendstream\\n"
    )
    result = run(input_path=str(pdf_file), output_path=str(out_file))

    assert out_file.exists()
    assert result["markdown_path"] == str(out_file)
    assert "Extracted Document" in out_file.read_text(encoding="utf-8")


def test_website_table_scraper_smoke(tmp_path: Path):
    source_dir = _copy_skill_to_tmp(tmp_path, "website-table-scraper")
    run = _load_run_func(source_dir, "website_table_scraper_main")

    html_file = tmp_path / "page.html"
    out_file = tmp_path / "page.tables.json"
    html_file.write_text(
        """
        <table>
          <tr><th>item</th><th>qty</th></tr>
          <tr><td>pens</td><td>4</td></tr>
        </table>
        """,
        encoding="utf-8",
    )
    result = run(input_path=str(html_file), output_path=str(out_file))

    assert out_file.exists()
    payload = json.loads(out_file.read_text(encoding="utf-8"))
    assert result["table_count"] == 1
    assert payload["tables"][0]["rows"][0]["item"] == "pens"


def test_mvp_skill_packaging_checks(tmp_path: Path):
    for slug in ("pdf-to-markdown", "website-table-scraper"):
        _copy_skill_to_tmp(tmp_path, slug)
        zip_path, sha = run_package(tmp_path, slug, output=None)

        assert zip_path.exists()
        assert len(sha) == 64
        assert ".skillforge/packages/" in zip_path.as_posix()
