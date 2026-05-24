"""
SkillForge AI — core data models.

These structures flow through every layer of the system:
  PermissionBroker, SkillBuilder, ValidationRunner, MCPController,
  AIOrchestrator, and the skillforge CLI.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------


class RiskLevel(str, Enum):
    """Three-tier risk classification for every action the AI can take."""
    SAFE = "safe"
    APPROVAL_REQUIRED = "approval_required"
    BLOCKED = "blocked"


class Mode(str, Enum):
    """Operating mode of the AI orchestrator."""
    BUILD = "build"
    RUN = "run"
    REPAIR = "repair"
    INSPECT = "inspect"
    PACKAGE = "package"
    BENCHMARK = "benchmark"
    ADMIN = "admin"
    UNKNOWN = "unknown"


class ValidationStatus(str, Enum):
    PENDING = "pending"
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"


# ---------------------------------------------------------------------------
# Skill manifest (SkillForge-layer schema, user-visible)
# ---------------------------------------------------------------------------


@dataclass
class InputSpec:
    name: str
    type: str  # file | string | number | boolean | array | object
    required: bool = True
    description: str = ""


@dataclass
class OutputSpec:
    name: str
    type: str
    description: str = ""


@dataclass
class SkillManifest:
    """
    User-facing schema for a skill.  Derived from ToolSpec but expressed in
    SkillForge vocabulary (permissions list, risk_level string, etc.).
    """
    name: str
    description: str
    category: str
    inputs: list[InputSpec] = field(default_factory=list)
    outputs: list[OutputSpec] = field(default_factory=list)
    tools_required: list[str] = field(default_factory=list)
    mcp_servers: list[str] = field(default_factory=list)
    permissions: list[str] = field(default_factory=list)
    risk_level: str = "low"
    validation: dict[str, str] = field(default_factory=lambda: {
        "syntax": ValidationStatus.PENDING,
        "tests": ValidationStatus.PENDING,
        "smoke": ValidationStatus.PENDING,
    })

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "inputs": [{"name": i.name, "type": i.type, "required": i.required, "description": i.description} for i in self.inputs],
            "outputs": [{"name": o.name, "type": o.type, "description": o.description} for o in self.outputs],
            "tools_required": self.tools_required,
            "mcp_servers": self.mcp_servers,
            "permissions": self.permissions,
            "risk_level": self.risk_level,
            "validation": {k: (v.value if isinstance(v, ValidationStatus) else v) for k, v in self.validation.items()},
        }


# ---------------------------------------------------------------------------
# Planning structures
# ---------------------------------------------------------------------------


@dataclass
class PlanStep:
    """A single atomic action in an orchestrator plan."""
    step_id: int
    action: str                          # e.g. "generate_spec", "scaffold_tool", "run_tests"
    description: str
    args: dict[str, Any] = field(default_factory=dict)
    risk_level: RiskLevel = RiskLevel.SAFE
    approval_required: bool = False


@dataclass
class Plan:
    """An ordered sequence of steps to fulfil a user request."""
    intent: str
    skill_name: str
    mode: Mode
    steps: list[PlanStep] = field(default_factory=list)

    def __iter__(self):
        return iter(self.steps)


@dataclass
class ApprovalRequest:
    """Tracks approval state for a single risky step."""
    step: PlanStep
    reason: str
    approved: bool | None = None  # None = pending, True = approved, False = denied


# ---------------------------------------------------------------------------
# Tool call schema
# ---------------------------------------------------------------------------


@dataclass
class ToolCallRequest:
    """
    Describes a single tool invocation that the AI wants to perform.
    Logged by EvidenceLogger before and after execution.
    """
    tool: str
    action: str
    arguments: dict[str, Any] = field(default_factory=dict)
    permissions_required: list[str] = field(default_factory=list)
    approval_required: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "tool": self.tool,
            "action": self.action,
            "arguments": self.arguments,
            "permissions_required": self.permissions_required,
            "approval_required": self.approval_required,
        }


# ---------------------------------------------------------------------------
# Validation report
# ---------------------------------------------------------------------------


@dataclass
class ValidationReport:
    """Aggregated result from ValidationRunner."""
    slug: str
    passed: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    attempt: int = 1
    # Per-validator results
    schema_ok: bool = True
    security_ok: bool = True
    mcp_ok: bool | None = None        # None = not checked (MCP disabled)
    skill_ok: bool = True
    tests_ok: bool = True
    safety_ok: bool = True

    def summary(self) -> str:
        status = "PASSED" if self.passed else "FAILED"
        parts = [f"[{status}] {self.slug} (attempt {self.attempt})"]
        if self.errors:
            for e in self.errors:
                parts.append(f"  ✗ {e}")
        if self.warnings:
            for w in self.warnings:
                parts.append(f"  ⚠ {w}")
        if self.passed:
            parts.append("  ✓ All validators passed")
        return "\n".join(parts)


# ---------------------------------------------------------------------------
# Intent parsing
# ---------------------------------------------------------------------------


@dataclass
class IntentResult:
    """Result of parsing a natural-language user message."""
    mode: Mode
    skill_name: str | None = None
    description: str = ""
    parameters: dict[str, Any] = field(default_factory=dict)
    raw_message: str = ""


# ---------------------------------------------------------------------------
# Orchestrator state
# ---------------------------------------------------------------------------


@dataclass
class OrchestratorState:
    """Mutable state carried across a chat session."""
    mode: Mode = Mode.UNKNOWN
    current_skill: str | None = None
    pending_plan: Plan | None = None
    approval_queue: list[ApprovalRequest] = field(default_factory=list)
    evidence_log_path: Path | None = None
    last_error: str | None = None
