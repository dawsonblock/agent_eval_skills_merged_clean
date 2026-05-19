"""
Security validator — checks a ToolSpec against the configured security policy.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from packages.core.tool_spec import ToolSpec, PrivacyLevel


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
    from ruamel.yaml import YAML
    yaml = YAML(typ="safe")
    with open(policy_path) as fh:
        return yaml.load(fh) or {}


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
    for allowed in (spec.security.allowed_read_paths or []) + (spec.security.allowed_write_paths or []):
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

    return violations


def enforce_security(spec: ToolSpec, policy_path: Path | None = None) -> None:
    """Raise SecurityViolation if spec fails policy checks."""
    violations = validate_security(spec, policy_path)
    if violations:
        raise SecurityViolation(violations)
