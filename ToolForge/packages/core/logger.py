"""
Structured logging for ToolForge.
JSON-formatted logs for production use, human-readable for development.
"""
import json
import logging
import sys
from datetime import datetime, timezone


class ToolForgeFormatter(logging.Formatter):
    """JSON formatter for structured logging."""

    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # Add any extra fields
        if hasattr(record, "tool_id"):
            log_data["tool_id"] = record.tool_id
        if hasattr(record, "context"):
            log_data["context"] = record.context

        return json.dumps(log_data, default=str)


def get_logger(name: str, level: str = "INFO") -> logging.Logger:
    """
    Get or create a logger instance.

    Args:
        name: Logger name (typically __name__)
        level: Logging level (DEBUG, INFO, WARNING, ERROR)

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level))

    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(ToolForgeFormatter())
        logger.addHandler(handler)

    return logger
