"""
PermissionBroker — three-tier safety gate for every action SkillForge AI takes.

Tier 1 — SAFE: auto-execute, no confirmation needed.
Tier 2 — APPROVAL_REQUIRED: prompt user for y/n in interactive mode; deny in
          non-interactive mode (or auto-approve when --yes flag is set).
Tier 3 — BLOCKED: always refused, regardless of flags.

Usage::

    broker = PermissionBroker(interactive=True, auto_approve=False)
    broker.check("create_skill_files")        # passes silently
    broker.check("run_shell_commands")        # raises ApprovalRequiredError
    broker.check("delete_arbitrary_files")    # raises PermissionDeniedError

    # Interactive approval loop:
    try:
        broker.check("install_python_packages")
    except ApprovalRequiredError as exc:
        decision = broker.request_approval(exc.step)  # prompts y/n
        if decision.approved:
            # proceed
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from skillforge_ai.models import ApprovalRequest, PlanStep, RiskLevel

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Exception types
# ---------------------------------------------------------------------------


class PermissionDeniedError(Exception):
    """Raised when an action falls in the BLOCKED tier."""

    def __init__(self, action: str) -> None:
        self.action = action
        super().__init__(
            f"Action '{action}' is permanently blocked by SkillForge security policy."
        )


class ApprovalRequiredError(Exception):
    """Raised when an action requires explicit user approval."""

    def __init__(self, action: str, step: PlanStep | None = None) -> None:
        self.action = action
        self.step = step or PlanStep(
            step_id=0,
            action=action,
            description=f"Action requires approval: {action}",
            risk_level=RiskLevel.APPROVAL_REQUIRED,
            approval_required=True,
        )
        super().__init__(
            f"Action '{action}' requires explicit approval before execution."
        )


# ---------------------------------------------------------------------------
# Action sets
# ---------------------------------------------------------------------------

# Actions that are always safe to execute without confirmation.
_SAFE_ACTIONS: frozenset[str] = frozenset({
    "create_skill_files",
    "write_skill_md",
    "write_metadata",
    "write_metadata_json",
    "generate_tests",
    "run_validators",
    "read_registry",
    "package_skills",
    "read_local_files",
    "parse_documents",
    "list_tools",
    "list_skills",
    "inspect_skill",
    "read_toolforge_yaml",
    "generate_spec",
    "scaffold_tool",
    "generate_mcp_server",
    "generate_skill_md",
    "generate_eval",
    "generate_docs",
    "register_skill",
    "run_pytest",
    "run_schema_validator",
    "run_security_validator",
    "run_mcp_validator",
    "run_skill_validator",
    "run_safety_analyzer",
    "mcp_list_tools",
    "mcp_smoke_test",
})

# Actions that require explicit y/n approval before execution.
_APPROVAL_REQUIRED_ACTIONS: frozenset[str] = frozenset({
    "install_npm_packages",
    "install_python_packages",
    "run_shell_commands",
    "start_docker",
    "stop_docker",
    "access_network",
    "write_outside_project",
    "call_external_apis",
    "use_secrets",
    "use_api_keys",
    "write_files",
    "overwrite_files",
    "mcp_call_tool",          # calling an installed MCP tool that may have side-effects
    "run_tool_in_sandbox",
    "run_eval_suite",
    "package_and_sign",
})

# Actions that are permanently blocked.
_BLOCKED_ACTIONS: frozenset[str] = frozenset({
    "delete_arbitrary_files",
    "delete_workspace",
    "run_unknown_binaries",
    "modify_system_folders",
    "exfiltrate_credentials",
    "exfiltrate_secrets",
    "execute_untrusted_code",
    "bypass_sandbox",
    "disable_safety_checks",
    "modify_permission_policy",
    "grant_elevated_permissions",
})


# ---------------------------------------------------------------------------
# PermissionBroker
# ---------------------------------------------------------------------------


class PermissionBroker:
    """
    Classifies actions and enforces the three-tier permission model.

    Parameters
    ----------
    interactive : bool
        When True, APPROVAL_REQUIRED actions prompt the user on stdin/stdout.
        When False, they are automatically denied unless auto_approve is set.
    auto_approve : bool
        When True, all APPROVAL_REQUIRED actions are auto-approved without
        prompting (equivalent to ``--yes`` CLI flag).  BLOCKED actions are
        never auto-approved.
    """

    def __init__(
        self,
        interactive: bool = True,
        auto_approve: bool = False,
    ) -> None:
        self._interactive = interactive
        self._auto_approve = auto_approve

    # ------------------------------------------------------------------
    # Classification
    # ------------------------------------------------------------------

    def classify(self, action: str) -> RiskLevel:
        """Return the risk tier for *action* (case-insensitive, normalised)."""
        normalised = action.lower().replace("-", "_").strip()
        if normalised in _BLOCKED_ACTIONS:
            return RiskLevel.BLOCKED
        if normalised in _APPROVAL_REQUIRED_ACTIONS:
            return RiskLevel.APPROVAL_REQUIRED
        if normalised in _SAFE_ACTIONS:
            return RiskLevel.SAFE
        # Unknown actions default to APPROVAL_REQUIRED for safety.
        logger.debug("Unknown action %r — defaulting to APPROVAL_REQUIRED", action)
        return RiskLevel.APPROVAL_REQUIRED

    # ------------------------------------------------------------------
    # Gate check
    # ------------------------------------------------------------------

    def check(self, action: str, step: PlanStep | None = None) -> None:
        """
        Enforce the permission policy for *action*.

        Raises
        ------
        PermissionDeniedError
            If the action is BLOCKED.
        ApprovalRequiredError
            If the action requires approval and approval has not yet been
            obtained (or auto_approve is False in non-interactive mode).
        """
        level = self.classify(action)

        if level == RiskLevel.BLOCKED:
            raise PermissionDeniedError(action)

        if level == RiskLevel.APPROVAL_REQUIRED:
            if self._auto_approve:
                logger.info("Auto-approving action: %s", action)
                return
            if not self._interactive:
                raise ApprovalRequiredError(action, step)
            # Interactive: raise and let caller handle the prompt via request_approval()
            raise ApprovalRequiredError(action, step)

        # RiskLevel.SAFE — no action needed

    # ------------------------------------------------------------------
    # Approval prompt
    # ------------------------------------------------------------------

    def request_approval(
        self,
        step: PlanStep,
        reason: str = "",
    ) -> ApprovalRequest:
        """
        Interactively prompt the user to approve or deny a risky step.

        Returns an ApprovalRequest with .approved set to True or False.
        This method blocks until the user responds.
        """
        req = ApprovalRequest(step=step, reason=reason or step.description)

        if self._auto_approve:
            req.approved = True
            return req

        if not self._interactive:
            req.approved = False
            return req

        # Print summary of the requested action
        print()
        print(f"  [APPROVAL REQUIRED]  Step {step.step_id}: {step.action}")
        print(f"  Description : {step.description}")
        print(f"  Risk level  : {step.risk_level.value}")
        if reason:
            print(f"  Reason      : {reason}")
        print()

        while True:
            try:
                answer = input("  Approve? [y/N] ").strip().lower()
            except (EOFError, KeyboardInterrupt):
                answer = "n"
            if answer in ("y", "yes"):
                req.approved = True
                break
            if answer in ("n", "no", ""):
                req.approved = False
                break
            print("  Please enter 'y' or 'n'.")

        return req

    # ------------------------------------------------------------------
    # Convenience helpers
    # ------------------------------------------------------------------

    def is_safe(self, action: str) -> bool:
        return self.classify(action) == RiskLevel.SAFE

    def is_blocked(self, action: str) -> bool:
        return self.classify(action) == RiskLevel.BLOCKED

    def safe_actions(self) -> frozenset[str]:
        return _SAFE_ACTIONS

    def approval_required_actions(self) -> frozenset[str]:
        return _APPROVAL_REQUIRED_ACTIONS

    def blocked_actions(self) -> frozenset[str]:
        return _BLOCKED_ACTIONS
