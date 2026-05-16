"""Regression tests for curated example tool specs."""
from __future__ import annotations

from pathlib import Path

from packages.core.tool_spec import ToolSpec


def test_all_example_specs_parse() -> None:
    examples_root = Path(__file__).resolve().parents[1] / "tools" / "examples"
    spec_files = sorted(examples_root.glob("*/toolforge.yaml"))

    assert spec_files, "expected curated example specs to exist"

    for spec_file in spec_files:
        spec = ToolSpec.from_yaml(spec_file)
        assert spec.slug
        assert all(isinstance(dep, str) for dep in spec.dependencies)