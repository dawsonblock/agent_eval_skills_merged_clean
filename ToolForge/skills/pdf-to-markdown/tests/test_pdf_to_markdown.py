from __future__ import annotations

from importlib import util as importlib_util
from pathlib import Path


def _load_run():
    module_path = Path(__file__).parent.parent / "tool" / "main.py"
    spec = importlib_util.spec_from_file_location(
        "pdf_to_markdown_main",
        module_path,
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load module at {module_path}")
    module = importlib_util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.run


def test_run_extracts_markdown(tmp_path: Path):
    run = _load_run()
    src = tmp_path / "doc.pdf"
    dst = tmp_path / "doc.md"
    src.write_bytes(
        b"%PDF-1.4\nstream\nQuarterly report summary line one.\nendstream\n"
    )

    result = run(input_path=str(src), output_path=str(dst))

    assert dst.exists()
    content = dst.read_text(encoding="utf-8")
    assert content.startswith("# Extracted Document")
    assert "Quarterly report summary" in content
    assert result["markdown_path"] == str(dst)
    assert result["characters"] == len(content)


def test_run_rejects_non_pdf(tmp_path: Path):
    run = _load_run()
    src = tmp_path / "doc.txt"
    src.write_text("hello", encoding="utf-8")

    try:
        run(input_path=str(src))
    except ValueError as exc:
        assert ".pdf" in str(exc)
    else:
        raise AssertionError("Expected ValueError for non-pdf input")
