"""
SkillForge AI — AI-controlled skill factory built on top of ToolForge.

Modules:
  models           — core data structures (RiskLevel, Mode, Plan, SkillManifest, …)
  evidence_logger  — structured JSONL evidence logger (per-session audit trail)
  permissions      — three-tier permission broker (safe / approval-required / blocked)
  skill_builder    — AI-driven skill scaffolding (wraps ToolForge generators)
  validation_runner— validate + auto-repair loop (generate → test → fail → patch → retest)
  mcp_controller   — MCP server lifecycle + JSON-RPC 2.0 tool calls over subprocess stdio
  tool_registry    — SkillForge-schema adapter over ToolRegistry
  orchestrator     — intent parser + mode dispatcher + AI control loop
"""

__version__ = "0.1.0"
