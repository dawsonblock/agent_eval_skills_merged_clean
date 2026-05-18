"""Tests for ToolForge custom exceptions."""
import pytest

from packages.core.errors import (
    ToolForgeError,
    SpecValidationError,
    MCPGenerationError,
    PackagingError,
)


def test_toolforge_error_basic():
    """Test basic ToolForgeError with just a message."""
    error = ToolForgeError("Test error")
    assert str(error) == "Test error"
    assert error.message == "Test error"
    assert error.context == {}
    assert error.hint is None


def test_toolforge_error_with_context():
    """Test ToolForgeError with context."""
    error = ToolForgeError("Test error", context={"key": "value"})
    assert "Test error" in str(error)
    assert "Context: {'key': 'value'}" in str(error)
    assert error.context == {"key": "value"}


def test_toolforge_error_with_hint():
    """Test ToolForgeError with hint."""
    error = ToolForgeError("Test error", hint="Try this instead")
    assert "Test error" in str(error)
    assert "Hint: Try this instead" in str(error)
    assert error.hint == "Try this instead"


def test_toolforge_error_with_context_and_hint():
    """Test ToolForgeError with both context and hint."""
    error = ToolForgeError(
        "Test error",
        context={"key": "value"},
        hint="Try this instead",
    )
    error_str = str(error)
    assert "Test error" in error_str
    assert "Context: {'key': 'value'}" in error_str
    assert "Hint: Try this instead" in error_str


def test_spec_validation_error():
    """Test SpecValidationError is a ToolForgeError."""
    error = SpecValidationError("Spec is invalid")
    assert isinstance(error, ToolForgeError)
    assert "Spec is invalid" in str(error)


def test_mcp_generation_error():
    """Test MCPGenerationError is a ToolForgeError."""
    error = MCPGenerationError("MCP generation failed")
    assert isinstance(error, ToolForgeError)
    assert "MCP generation failed" in str(error)


def test_packaging_error():
    """Test PackagingError is a ToolForgeError."""
    error = PackagingError("Packaging failed")
    assert isinstance(error, ToolForgeError)
    assert "Packaging failed" in str(error)
