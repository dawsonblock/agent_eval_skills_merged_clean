"""
Security validator — checks a ToolSpec against the configured security policy.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from packages.core.tool_spec import ToolSpec, PrivacyLevel, ToolCapability
from skillforge_ai.yaml_utils import load_yaml


class SecurityViolation(Exception):
    def __init__(self, violations: list[str]) -> None:
        self.violations = violations
        super().__init__("\n".join(violations))


def _load_policy(policy_path: Path | None = None) -> dict[str, Any]:
    """Load security_policy.yaml; falls back to defaults if not found."""
    if policy_path is None:
        policy_path = Path(__file__).parent.parent.parent / "configs" / "security_policy.yaml"
    if not policy_path.exists():
        return {}
    return load_yaml(policy_path) or {}


_PATH_TRAVERSAL_RE = re.compile(r"(^|[\\/])\.\.([\\/]|$)")


def _normalize_command(value: str) -> str:
    return " ".join(value.lower().split())


def _command_matches_pattern(command: str, pattern: str) -> bool:
    cmd = _normalize_command(command)
    pat = _normalize_command(pattern)
    if not pat:
        return False
    if "|" in pat or " " in pat or "+" in pat:
        return pat in cmd
    return cmd.split(" ", 1)[0] == pat


def validate_security(spec: ToolSpec, policy_path: Path | None = None) -> list[str]:
    """
    Check *spec* against security policy.
    Returns a list of violation strings (empty = compliant).
    """
    policy = _load_policy(policy_path)
    violations: list[str] = []

    execution_policy = policy.get("execution", {})

    # Check minimum sandbox level for capabilities
    min_level = execution_policy.get("capability_min_sandbox_level", {})
    for cap in spec.security.required_capabilities:
        cap_key = cap.value  # e.g. "run_shell"
        required_lvl = min_level.get(cap_key, 0)
        if spec.sandbox_level < required_lvl:
            violations.append(
                f"Capability '{cap.value}' requires sandbox_level >= {required_lvl}, "
                f"but spec declares {spec.sandbox_level}"
            )

    # Check denied Python imports
    # (actual import scan is done by safety_analyzer; here we check spec-level)

    # Capabilities must be coherent with declared network intent.
    if (
        ToolCapability.CALL_HTTP in spec.security.required_capabilities
        and not spec.security.requires_network
    ):
        violations.append("Capability 'call_http' requires requires_network=true")

    if not spec.security.requires_network and (
        spec.security.allowed_domains or spec.security.blocked_domains
    ):
        violations.append("Network domain rules are set but requires_network=false")

    # Check privacy level / approval
    if spec.security.privacy_level in (PrivacyLevel.SENSITIVE, PrivacyLevel.EVIDENCE_GRADE):
        if not spec.security.approved_by:
            violations.append(
                f"Privacy level '{spec.security.privacy_level}' requires 'approved_by' to be set"
            )

    # Secrets in allowed_paths — use proper path-prefix comparison so that
    # a blocked path of '/etc' does not incorrectly match '/etc_data/'.
    fs_policy = policy.get("filesystem", {})
    blocked_paths: list[str] = fs_policy.get("deny_system_paths", [])
    secret_fragments = (
        "~/.ssh",
        "~/.aws",
        "~/.config",
        "/.ssh/",
        "/.aws/",
        "/.config/",
    )
    deny_path_traversal = bool(fs_policy.get("deny_path_traversal", True))

    for allowed in (spec.security.allowed_read_paths or []) + (
        spec.security.allowed_write_paths or []
    ):
        if deny_path_traversal and _PATH_TRAVERSAL_RE.search(allowed):
            violations.append(f"allowed_path '{allowed}' contains path traversal segments")

        normalized_path = allowed.replace("\\", "/").lower()
        for fragment in secret_fragments:
            if fragment in normalized_path:
                violations.append(
                    f"allowed_path '{allowed}' references a protected secret/config location"
                )
                break

        allowed_path = Path(allowed)
        for blocked in blocked_paths:
            blocked_path = Path(blocked.rstrip("/**").rstrip("/*"))
            try:
                allowed_path.relative_to(blocked_path)
                overlaps = True
            except ValueError:
                overlaps = False
            if overlaps:
                violations.append(
                    f"allowed_path '{allowed}' overlaps blocked system path '{blocked}'"
                )

    # Absolute write paths are not allowed in portable specs; writes must remain
    # within explicit workspace-relative roots.
    for allowed in spec.security.allowed_write_paths or []:
        normalized = allowed.replace("\\", "/")
        if normalized.startswith("/") or re.match(r"^[A-Za-z]:[/\\]", allowed):
            violations.append(f"allowed_write_path '{allowed}' must be workspace-relative")

    shell_policy = policy.get("shell", {})
    blocked_command_patterns = list(shell_policy.get("blocked_commands", []))
    # Ensure critical shell patterns are always blocked, even if policy is edited.
    for required_pattern in ("rm -rf", "curl | sh", "wget | sh", "chmod +s", "sudo", "su"):
        if required_pattern not in blocked_command_patterns:
            blocked_command_patterns.append(required_pattern)

    for cmd in spec.security.allowed_commands or []:
        for blocked_pattern in blocked_command_patterns:
            if _command_matches_pattern(cmd, blocked_pattern):
                violations.append(
                    f"allowed_commands entry '{cmd}' matches blocked pattern '{blocked_pattern}'"
                )
                break

    return violations


def enforce_security(spec: ToolSpec, policy_path: Path | None = None) -> None:
    """Raise SecurityViolation if spec fails policy checks."""
    violations = validate_security(spec, policy_path)
    if violations:
        raise SecurityViolation(violations)
