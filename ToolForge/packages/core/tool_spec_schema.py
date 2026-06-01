"""
ToolSpec Schema Validation — strict validation rules for AI-generated specs.

This module defines validation rules and schema constraints for ToolSpec objects,
ensuring AI-generated specs meet security and quality requirements.

IMPORTANT: AI ROLE BOUNDARIES
- All AI-generated specs must pass these validation rules before being used
- Validation is mandatory; no bypassing or disabling
- Default values enforce security by default (shell/network disabled)
- See ToolForge/docs/AI_ROLE_BOUNDARIES.md for full boundaries
"""

from __future__ import annotations

from enum import Enum

from packages.core.tool_spec import (
    ToolCapability,
    ToolSpec,
)


class ValidationSeverity(str, Enum):
    """Severity level for validation errors."""

    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class SpecValidationError:
    """A single validation error or warning."""

    def __init__(
        self,
        field: str,
        message: str,
        severity: ValidationSeverity = ValidationSeverity.ERROR,
    ) -> None:
        self.field = field
        self.message = message
        self.severity = severity

    def __repr__(self) -> str:
        return f"SpecValidationError(field={self.field!r}, message={self.message!r}, severity={self.severity})"


class SpecSchemaValidator:
    """
    Validates ToolSpec objects against strict schema rules.

    Enforces:
    - Required fields are present
    - Default security values (shell/network disabled by default)
    - Path protection rules
    - Capability restrictions
    - Minimum test/eval requirements
    """

    # Minimum requirements
    MIN_PARAMETERS = 1
    MIN_EVAL_CASES = 3
    MIN_TEST_CASES = 1

    # Default blocked paths (path traversal protection)
    DEFAULT_BLOCKED_PATHS = [
        "~/.ssh/**",
        "~/.aws/**",
        "~/.config/**",
        "/etc/**",
        "/var/**",
        "/root/**",
        "/sys/**",
        "/proc/**",
    ]

    # Default blocked commands
    DEFAULT_BLOCKED_COMMANDS = [
        "rm",
        "sudo",
        "chmod",
        "chown",
        "curl",
        "wget",
        "ssh",
        "scp",
        "kubectl",
        "docker",
        "aws",
    ]

    def validate(self, spec: ToolSpec) -> list[SpecValidationError]:
        """
        Validate a ToolSpec against all schema rules.

        Returns a list of validation errors/warnings.
        Empty list means validation passed.
        """
        errors: list[SpecValidationError] = []

        # Required fields
        errors.extend(self._validate_required_fields(spec))

        # Security defaults
        errors.extend(self._validate_security_defaults(spec))

        # Capability restrictions
        errors.extend(self._validate_capabilities(spec))

        # Path protection
        errors.extend(self._validate_path_protection(spec))

        # Parameter validation
        errors.extend(self._validate_parameters(spec))

        # Eval/test requirements
        errors.extend(self._validate_eval_requirements(spec))

        return errors

    def _validate_required_fields(self, spec: ToolSpec) -> list[SpecValidationError]:
        """Validate that required fields are present and non-empty."""
        errors: list[SpecValidationError] = []

        if not spec.name or not spec.name.strip():
            errors.append(
                SpecValidationError("name", "Tool name is required and must not be empty")
            )

        if not spec.slug or not spec.slug.strip():
            errors.append(
                SpecValidationError("slug", "Tool slug is required and must not be empty")
            )

        if not spec.description or not spec.description.strip():
            errors.append(
                SpecValidationError(
                    "description", "Tool description is required and must not be empty"
                )
            )

        if not spec.version or not spec.version.strip():
            errors.append(
                SpecValidationError("version", "Tool version is required and must not be empty")
            )

        if not spec.language:
            errors.append(SpecValidationError("language", "Tool language is required"))

        if not spec.entry_point or not spec.entry_point.strip():
            errors.append(SpecValidationError("entry_point", "Tool entry point is required"))

        # Security spec is mandatory
        if not spec.security:
            errors.append(SpecValidationError("security", "Security spec is required"))

        return errors

    def _validate_security_defaults(self, spec: ToolSpec) -> list[SpecValidationError]:
        """
        Validate security defaults enforce secure-by-default behavior.

        - Shell execution should be disabled unless explicitly requested
        - Network access should be disabled unless explicitly requested
        - Filesystem access should be disabled unless explicitly requested
        """
        errors: list[SpecValidationError] = []

        if not spec.security:
            return errors

        # Warn if shell is enabled (should be explicit)
        if spec.security.requires_shell:
            errors.append(
                SpecValidationError(
                    "security.requires_shell",
                    "Shell execution is enabled; ensure this is necessary and approved",
                    ValidationSeverity.WARNING,
                )
            )

        # Warn if network is enabled (should be explicit)
        if spec.security.requires_network:
            errors.append(
                SpecValidationError(
                    "security.requires_network",
                    "Network access is enabled; ensure this is necessary and approved",
                    ValidationSeverity.WARNING,
                )
            )

        # Warn if filesystem is enabled without explicit paths
        if spec.security.requires_filesystem:
            if not spec.security.allowed_read_paths and not spec.security.allowed_write_paths:
                errors.append(
                    SpecValidationError(
                        "security.allowed_read_paths",
                        "Filesystem access is enabled but no paths are specified; "
                        "add explicit allowed_read_paths and/or allowed_write_paths",
                        ValidationSeverity.WARNING,
                    )
                )

        # Validate blocked paths are present
        if not spec.security.blocked_paths:
            errors.append(
                SpecValidationError(
                    "security.blocked_paths",
                    "Blocked paths list is empty; should include default blocked paths",
                    ValidationSeverity.WARNING,
                )
            )

        # Validate blocked commands are present
        if not spec.security.blocked_commands:
            errors.append(
                SpecValidationError(
                    "security.blocked_commands",
                    "Blocked commands list is empty; should include default blocked commands",
                    ValidationSeverity.WARNING,
                )
            )

        return errors

    def _validate_capabilities(self, spec: ToolSpec) -> list[SpecValidationError]:
        """
        Validate that capabilities are from the allowed set.

        Rejects unknown capabilities that could bypass security controls.
        """
        errors: list[SpecValidationError] = []

        if not spec.security:
            return errors

        valid_capabilities = {cap.value for cap in ToolCapability}

        for cap in spec.security.required_capabilities:
            if isinstance(cap, str):
                if cap not in valid_capabilities:
                    errors.append(
                        SpecValidationError(
                            f"security.required_capabilities.{cap}",
                            f"Unknown capability: {cap!r}. "
                            f"Valid capabilities: {sorted(valid_capabilities)}",
                        )
                    )

        return errors

    def _validate_path_protection(self, spec: ToolSpec) -> list[SpecValidationError]:
        """
        Validate path protection rules.

        - Ensure blocked paths include sensitive system directories
        - Warn if allowed paths include potentially dangerous patterns
        """
        errors: list[SpecValidationError] = []

        if not spec.security:
            return errors

        # Check if default blocked paths are included
        spec_blocked = set(spec.security.blocked_paths or [])
        missing_blocked = set(self.DEFAULT_BLOCKED_PATHS) - spec_blocked

        if missing_blocked:
            errors.append(
                SpecValidationError(
                    "security.blocked_paths",
                    f"Missing default blocked paths: {sorted(missing_blocked)}",
                    ValidationSeverity.WARNING,
                )
            )

        # Warn if allowed paths include dangerous patterns
        dangerous_patterns = ["~/.ssh", "~/.aws", "/etc", "/var", "/root", "/sys", "/proc"]
        for pattern in spec.security.allowed_read_paths or []:
            for dangerous in dangerous_patterns:
                if dangerous in pattern:
                    errors.append(
                        SpecValidationError(
                            f"security.allowed_read_paths.{pattern}",
                            f"Allowed path pattern includes potentially dangerous path: {dangerous}",
                            ValidationSeverity.WARNING,
                        )
                    )

        for pattern in spec.security.allowed_write_paths or []:
            for dangerous in dangerous_patterns:
                if dangerous in pattern:
                    errors.append(
                        SpecValidationError(
                            f"security.allowed_write_paths.{pattern}",
                            f"Allowed path pattern includes potentially dangerous path: {dangerous}",
                            ValidationSeverity.ERROR,
                        )
                    )

        return errors

    def _validate_parameters(self, spec: ToolSpec) -> list[SpecValidationError]:
        """
        Validate parameter definitions.

        - Ensure minimum number of parameters
        - Validate parameter types
        - Check for path input parameters that need special handling
        """
        errors: list[SpecValidationError] = []

        if not spec.parameters:
            errors.append(
                SpecValidationError(
                    "parameters",
                    f"At least {self.MIN_PARAMETERS} parameter is required",
                )
            )
            return errors

        if len(spec.parameters) < self.MIN_PARAMETERS:
            errors.append(
                SpecValidationError(
                    "parameters",
                    f"At least {self.MIN_PARAMETERS} parameter is required, got {len(spec.parameters)}",
                )
            )

        # Validate each parameter
        for i, param in enumerate(spec.parameters):
            if not param.name or not param.name.strip():
                errors.append(
                    SpecValidationError(
                        f"parameters[{i}].name",
                        "Parameter name is required",
                    )
                )

            if not param.type or not param.type.strip():
                errors.append(
                    SpecValidationError(
                        f"parameters[{i}].type",
                        "Parameter type is required",
                    )
                )

            # Check for path-type parameters that need special handling
            if "path" in param.name.lower() or param.type in ["path", "file"]:
                errors.append(
                    SpecValidationError(
                        f"parameters[{i}].name",
                        f"Parameter '{param.name}' appears to be a path/file parameter; "
                        "ensure security spec includes appropriate path restrictions",
                        ValidationSeverity.WARNING,
                    )
                )

        return errors

    def _validate_eval_requirements(self, spec: ToolSpec) -> list[SpecValidationError]:
        """
        Validate eval and test requirements.

        - Ensure minimum number of eval cases
        - Ensure eval spec is present
        """
        errors: list[SpecValidationError] = []

        # Eval spec should be present
        if not spec.eval:
            errors.append(
                SpecValidationError(
                    "eval",
                    "Eval spec is required for tool validation",
                    ValidationSeverity.WARNING,
                )
            )
        else:
            # Check minimum eval cases
            if hasattr(spec.eval, "cases") and spec.eval.cases:
                if len(spec.eval.cases) < self.MIN_EVAL_CASES:
                    errors.append(
                        SpecValidationError(
                            "eval.cases",
                            f"At least {self.MIN_EVAL_CASES} eval cases are required, got {len(spec.eval.cases)}",
                            ValidationSeverity.WARNING,
                        )
                    )
            else:
                errors.append(
                    SpecValidationError(
                        "eval.cases",
                        f"At least {self.MIN_EVAL_CASES} eval cases are required",
                        ValidationSeverity.WARNING,
                    )
                )

        return errors


def validate_tool_spec_schema(spec: ToolSpec) -> list[SpecValidationError]:
    """
    Convenience function to validate a ToolSpec against schema rules.

    Returns a list of validation errors/warnings.
    Empty list means validation passed.
    """
    validator = SpecSchemaValidator()
    return validator.validate(spec)
