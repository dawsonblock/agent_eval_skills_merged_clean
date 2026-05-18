"""Tests for doc generator."""
from pathlib import Path

import pytest

from packages.core.doc_generator import generate_docs
from packages.core.tool_spec import ToolSpec, ToolLanguage, ParameterSpec, OutputSpec


def test_generate_docs_creates_readme(tmp_path: Path) -> None:
    """Test that generate_docs creates a README.md file."""
    spec = ToolSpec(
        name="test-tool",
        slug="test-tool",
        version="0.1.0",
        description="A test tool",
        language=ToolLanguage.PYTHON,
        parameters=[ParameterSpec(name="input", type="string", description="Test input")],
        output=OutputSpec(type="string", description="Test output"),
    )
    
    result = generate_docs(spec, tmp_path)
    
    assert len(result) == 1
    readme_path = result[0]
    assert readme_path.name == "README.md"
    assert readme_path.exists()
    assert readme_path.parent.name == "test-tool"


def test_generate_docs_overwrite_behavior(tmp_path: Path) -> None:
    """Test that generate_docs respects overwrite flag."""
    spec = ToolSpec(
        name="test-tool",
        slug="test-tool",
        version="0.1.0",
        description="A test tool",
        language=ToolLanguage.PYTHON,
        parameters=[ParameterSpec(name="input", type="string", description="Test input")],
        output=OutputSpec(type="string", description="Test output"),
    )
    
    # First write
    result1 = generate_docs(spec, tmp_path, overwrite=False)
    assert len(result1) == 1
    
    # Second write without overwrite should raise FileExistsError
    with pytest.raises(FileExistsError):
        generate_docs(spec, tmp_path, overwrite=False)
    
    # Third write with overwrite should succeed
    result3 = generate_docs(spec, tmp_path, overwrite=True)
    assert len(result3) == 1


def test_generate_docs_content_includes_spec_info(tmp_path: Path) -> None:
    """Test that generated README includes spec information."""
    spec = ToolSpec(
        name="test-tool",
        slug="test-tool",
        version="0.1.0",
        description="A test tool for testing",
        language=ToolLanguage.PYTHON,
        parameters=[ParameterSpec(name="input", type="string", description="Test input")],
        output=OutputSpec(type="string", description="Test output"),
    )
    
    result = generate_docs(spec, tmp_path)
    readme_path = result[0]
    content = readme_path.read_text(encoding="utf-8")
    
    assert "test-tool" in content
    assert "0.1.0" in content
    assert "A test tool for testing" in content
