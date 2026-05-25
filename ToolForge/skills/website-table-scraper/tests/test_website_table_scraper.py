from __future__ import annotations

import json
from importlib import util as importlib_util
from pathlib import Path


def _load_run():
    module_path = Path(__file__).parent.parent / "tool" / "main.py"
    spec = importlib_util.spec_from_file_location(
        "website_table_scraper_main",
        module_path,
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load module at {module_path}")
    module = importlib_util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.run


def test_run_extracts_tables(tmp_path: Path):
    run = _load_run()
    src = tmp_path / "scores.html"
    dst = tmp_path / "scores.json"
    src.write_text(
        """
        <html><body>
          <table>
            <tr><th>name</th><th>score</th></tr>
            <tr><td>alice</td><td>98</td></tr>
            <tr><td>bob</td><td>91</td></tr>
          </table>
        </body></html>
        """,
        encoding="utf-8",
    )

    result = run(input_path=str(src), output_path=str(dst))

    assert dst.exists()
    data = json.loads(dst.read_text(encoding="utf-8"))
    assert result["json_path"] == str(dst)
    assert result["table_count"] == 1
    assert data["tables"][0]["rows"][0]["name"] == "alice"


def test_run_rejects_non_html(tmp_path: Path):
    run = _load_run()
    src = tmp_path / "scores.txt"
    src.write_text("not html", encoding="utf-8")

    try:
        run(input_path=str(src))
    except ValueError as exc:
        assert ".html" in str(exc)
    else:
        raise AssertionError("Expected ValueError for non-html input")
