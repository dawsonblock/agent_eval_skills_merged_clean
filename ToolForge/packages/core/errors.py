"""
Custom exceptions with better error context and debugging hints.
"""

from typing import Any, Optional


class ToolForgeError(Exception):
    """Base exception for ToolForge with context."""

    def __init__(
        self,
        message: str,
        context: Optional[dict[str, Any]] = None,
        hint: Optional[str] = None,
    ) -> None:
        self.message = message
        self.context = context or {}
        self.hint = hint
        super().__init__(self._format_message())

    def _format_message(self) -> str:
        msg = self.message
        if self.context:
            msg += f"\nContext: {self.context}"
        if self.hint:
            msg += f"\nHint: {self.hint}"
        return msg


class SpecValidationError(ToolForgeError):
    """ToolSpec validation failed."""

    pass


class MCPGenerationError(ToolForgeError):
    """MCP server generation failed."""

    pass


class PackagingError(ToolForgeError):
    """Tool packaging failed."""

    pass
