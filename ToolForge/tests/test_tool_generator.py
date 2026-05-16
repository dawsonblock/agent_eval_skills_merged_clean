"""Unit tests for packages.core.tool_generator."""
from __future__ import annotations

from pathlib import Path

import pytest

from packages.core.tool_generator import scaffold_tool
from packages.core.tool_spec import ParameterSpec, ToolLanguage, ToolSpec


def _make_spec(**kwargs) -> ToolSpec:
    defaults = dict(
        name="Test Tool",
        slug="test-tool",
        version="0.1.0",
        description="A test tool",
        language=ToolLanguage.PYTHON,
        entry_point="tool.py",
        parameters=[ParameterSpec(name="input", type="string", description="Input")],
    )
    defaults.update(kwargs)
    return ToolSpec(**defaults)


def test_scaffold_creates_expected_files(tmp_path: Path) -> None:
    spec = _make_spec()
    created = scaffold_tool(spec, tmp_path)

    paths = {p.name for p in created}
    assert "toolforge.yaml" in paths
    assert "tool.py" in paths
    assert "README.md" in paths


def test_scaffold_creates_test_file(tmp_path: Path) -> None:
    spec = _make_spec()
    created = scaffold_tool(spec, tmp_path)
    names = [p.name for p in created]
    assert any("test_" in n for n in names)


def test_scaffold_no_overwrite_raises(tmp_path: Path) -> None:
    spec = _make_spec()
    scaffold_tool(spec, tmp_path)
    with pytest.raises(FileExistsError):
        scaffold_tool(spec, tmp_path, overwrite=False)


def test_scaffold_overwrite_succeeds(tmp_path: Path) -> None:
    spec = _make_spec()
    scaffold_tool(spec, tmp_path)
    # Should not raise
    scaffold_tool(spec, tmp_path, overwrite=True)


def test_scaffold_output_under_slug_dir(tmp_path: Path) -> None:
    spec = _make_spec()
    created = scaffold_tool(spec, tmp_path)
    for p in created:
        assert spec.slug in str(p), f"Expected slug in path: {p}"


def test_csv_cleaner_generation_uses_file_params(tmp_path: Path) -> None:
    spec = _make_spec(
        name="CSV Cleaner",
        slug="csv-cleaner",
        parameters=[
            ParameterSpec(
                name="input_path",
                type="string",
                description="Input CSV path",
            ),
            ParameterSpec(
                name="output_path",
                type="string",
                description="Output CSV path",
                required=False,
                default="outputs/cleaned.csv",
            ),
        ],
    )
    scaffold_tool(spec, tmp_path)
    tool_file = tmp_path / "csv-cleaner" / "tool.py"
    content = tool_file.read_text(encoding="utf-8")
    assert "def run(input_path: str, output_path: str | None = None)" in content
    assert "def run(input: str = \"\")" not in content


def test_csv_cleaner_scaffolds_examples(tmp_path: Path) -> None:
    spec = _make_spec(name="CSV Cleaner", slug="csv-cleaner")
    scaffold_tool(spec, tmp_path)
    base = tmp_path / "csv-cleaner"
    assert (base / "examples" / "input.csv").exists()
    assert (base / "examples" / "empty.csv").exists()
