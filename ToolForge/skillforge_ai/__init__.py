"""
SkillForge AI — AI-controlled skill factory built on top of ToolForge.

Modules:
  models           — core data structures and enums
  evidence_logger  — structured JSONL evidence logging
  permissions      — permission broker and approval checks
  skill_builder    — AI-driven skill scaffolding
  validation_runner — validation and auto-repair loop
  mcp_controller   — MCP lifecycle and JSON-RPC tool calls
  tool_registry    — SkillForge adapter over ToolRegistry
  orchestrator     — intent parsing and mode dispatch
"""

from .cli import main as cli_main

__version__ = "0.1.0"

__all__ = ["__version__", "cli_main"]
