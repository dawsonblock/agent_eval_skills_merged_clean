"""Unit tests for packages.core.mcp_generator."""
from __future__ import annotations

from pathlib import Path

import pytest

from packages.core.mcp_generator import generate_mcp_server
from packages.core.tool_spec import MCPSpec, ParameterSpec, ToolLanguage, ToolSpec


def _make_spec(language: ToolLanguage = ToolLanguage.PYTHON) -> ToolSpec:
    return ToolSpec(
        name="MCP Test",
        slug="mcp-test",
        version="0.1.0",
        description="A test MCP tool",
        language=language,
        entry_point="tool.py",
        parameters=[ParameterSpec(name="query", type="string", description="Query input")],
        mcp=MCPSpec(enabled=True, transport="stdio"),
    )


def test_python_mcp_creates_server_py(tmp_path: Path) -> None:
    spec = _make_spec(ToolLanguage.PYTHON)
    created = generate_mcp_server(spec, tmp_path)
    names = {p.name for p in created}
    assert "server.py" in names


def test_python_mcp_creates_pyproject_toml(tmp_path: Path) -> None:
    spec = _make_spec(ToolLanguage.PYTHON)
    created = generate_mcp_server(spec, tmp_path)
    names = {p.name for p in created}
    assert "pyproject.toml" in names


def test_typescript_mcp_creates_index_ts(tmp_path: Path) -> None:
    spec = _make_spec(ToolLanguage.TYPESCRIPT)
    created = generate_mcp_server(spec, tmp_path)
    names = {p.name for p in created}
    assert "index.ts" in names


def test_dockerfile_always_created(tmp_path: Path) -> None:
    spec = _make_spec(ToolLanguage.PYTHON)
    created = generate_mcp_server(spec, tmp_path)
    names = {p.name for p in created}
    assert "Dockerfile" in names


def test_output_under_slug_dir(tmp_path: Path) -> None:
    spec = _make_spec()
    created = generate_mcp_server(spec, tmp_path)
    for p in created:
        assert spec.slug in str(p)
