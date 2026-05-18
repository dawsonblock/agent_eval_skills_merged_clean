"""Tests for ToolForge logger."""
import json
import logging

from packages.core.logger import get_logger, ToolForgeFormatter


def test_get_logger_creates_logger():
    """Test that get_logger creates a logger instance."""
    logger = get_logger("test_logger")
    assert logger is not None
    assert logger.name == "test_logger"
    assert logger.level == logging.INFO


def test_get_logger_with_debug_level():
    """Test that get_logger respects level parameter."""
    logger = get_logger("test_debug_logger", level="DEBUG")
    assert logger.level == logging.DEBUG


def test_get_logger_same_instance():
    """Test that get_logger returns the same instance for the same name."""
    logger1 = get_logger("test_same_logger")
    logger2 = get_logger("test_same_logger")
    assert logger1 is logger2


def test_toolforge_formatter_basic():
    """Test basic ToolForgeFormatter output."""
    formatter = ToolForgeFormatter()
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname="test.py",
        lineno=1,
        msg="Test message",
        args=(),
        exc_info=None,
    )
    output = formatter.format(record)
    log_data = json.loads(output)
    
    assert log_data["level"] == "INFO"
    assert log_data["logger"] == "test"
    assert log_data["message"] == "Test message"
    assert "timestamp" in log_data
    assert log_data["module"] == "test"
    assert log_data["function"] is None or log_data["function"] == "<module>"


def test_toolforge_formatter_with_exception():
    """Test ToolForgeFormatter includes exception info."""
    formatter = ToolForgeFormatter()
    try:
        raise ValueError("Test exception")
    except ValueError:
        import sys
        exc_info = sys.exc_info()
        
    record = logging.LogRecord(
        name="test",
        level=logging.ERROR,
        pathname="test.py",
        lineno=1,
        msg="Error occurred",
        args=(),
        exc_info=exc_info,
    )
    output = formatter.format(record)
    log_data = json.loads(output)
    
    assert "exception" in log_data
    assert "ValueError" in log_data["exception"]


def test_toolforge_formatter_with_extra_fields():
    """Test ToolForgeFormatter includes extra fields."""
    formatter = ToolForgeFormatter()
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname="test.py",
        lineno=1,
        msg="Test message",
        args=(),
        exc_info=None,
    )
    record.tool_id = "test-tool"
    record.context = {"key": "value"}
    
    output = formatter.format(record)
    log_data = json.loads(output)
    
    assert log_data["tool_id"] == "test-tool"
    assert log_data["context"] == {"key": "value"}
