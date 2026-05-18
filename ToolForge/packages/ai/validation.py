"""
Validation pipeline for AI-generated tool specs.

Provides schema, security, MCP, SKILL, and parameter validation.

IMPORTANT: AI ROLE BOUNDARIES
- All AI-generated specs must pass this validation before being used
- Validation is mandatory; no bypassing or disabling
- AI must not suggest reducing validation requirements
- See ToolForge/docs/AI_ROLE_BOUNDARIES.md for full boundaries
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from packages.core.tool_spec import ToolSpec


class Severity(str, Enum):
    """Severity level for validation issues."""

    ERROR = "error"
    WARNING = "warning"


@dataclass
class ValidationError:
    """A single validation error with context."""

    field: str
    message: str
    severity: Severity


@dataclass
class ValidationResult:
    """Result of validating a ToolSpec."""

    is_valid: bool
    errors: list[ValidationError]
    warnings: list[ValidationError]

    def add_error(self, field: str, message: str) -> None:
        """Add an error to the result."""
        self.errors.append(ValidationError(field=field, message=message, severity=Severity.ERROR))
        self.is_valid = False

    def add_warning(self, field: str, message: str) -> None:
        """Add a warning to the result."""
        self.warnings.append(ValidationError(field=field, message=message, severity=Severity.WARNING))

    def has_errors(self) -> bool:
        """Check if there are any errors."""
        return len(self.errors) > 0

    def has_warnings(self) -> bool:
        """Check if there are any warnings."""
        return len(self.warnings) > 0


class SpecValidator:
    """Comprehensive validator for ToolSpec objects."""

    def validate(self, spec: ToolSpec) -> ValidationResult:
        """
        Validate a ToolSpec across all layers.

        Returns ValidationResult with errors and warnings.
        """
        result = ValidationResult(is_valid=True, errors=[], warnings=[])

        # Layer 1: Pydantic model validation (already done by model_validate)
        # This is implicit in the spec object creation

        # Layer 2: Structural validation
        self._validate_structure(spec, result)

        # Layer 3: Security policy validation
        self._validate_security(spec, result)

        # Layer 4: Eval case validation
        self._validate_eval(spec, result)

        # Layer 5: MCP/SKILL validation
        self._validate_mcp_skill(spec, result)

        # Layer 6: Parameter validation
        self._validate_parameters(spec, result)

        return result

    def _validate_structure(self, spec: ToolSpec, result: ValidationResult) -> None:
        """Validate basic structure and required fields."""
        if not spec.name or not spec.name.strip():
            result.add_error("name", "Tool name cannot be empty")

        if not spec.slug or not spec.slug.strip():
            result.add_error("slug", "Tool slug cannot be empty")

        if not spec.description or not spec.description.strip():
            result.add_warning("description", "Tool description is empty")

        if not spec.version:
            result.add_error("version", "Tool version is required")

        if not spec.language:
            result.add_error("language", "Tool language is required")

        if not spec.entry_point:
            result.add_error("entry_point", "Entry point is required")

    def _validate_security(self, spec: ToolSpec, result: ValidationResult) -> None:
        """Validate security policy configuration."""
        if not spec.security:
            result.add_error("security", "Security spec is required")
            return

        sec = spec.security

        # Validate path patterns
        if sec.requires_filesystem:
            if not sec.allowed_read_paths:
                result.add_warning(
                    "security.allowed_read_paths",
                    "Filesystem access enabled but no read paths specified",
                )
            if not sec.allowed_write_paths:
                result.add_warning(
                    "security.allowed_write_paths",
                    "Filesystem access enabled but no write paths specified",
                )

        # Validate file size limits
        if sec.max_file_size_mb and sec.max_file_size_mb < 0:
            result.add_error("security.max_file_size_mb", "Max file size must be non-negative")

        # Validate privacy level
        if not sec.privacy_level:
            result.add_warning("security.privacy_level", "Privacy level not specified")

    def _validate_eval(self, spec: ToolSpec, result: ValidationResult) -> None:
        """Validate eval harness configuration."""
        if not spec.eval:
            result.add_warning("eval", "Eval harness not configured")
            return

        eval_spec = spec.eval

        if eval_spec.enabled and not eval_spec.cases:
            result.add_warning("eval.cases", "Eval enabled but no test cases defined")

        if eval_spec.baseline_pass_rate < 0 or eval_spec.baseline_pass_rate > 1:
            result.add_error(
                "eval.baseline_pass_rate",
                "Baseline pass rate must be between 0 and 1",
            )

        # Validate each eval case
        for i, case in enumerate(eval_spec.cases):
            case_prefix = f"eval.cases[{i}]"
            if not case.id:
                result.add_error(f"{case_prefix}.id", "Eval case ID is required")

            if not case.description:
                result.add_warning(f"{case_prefix}.description", "Eval case description is empty")

            if not case.inputs:
                result.add_error(f"{case_prefix}.inputs", "Eval case inputs are required")

            if case.expected_success is None:
                result.add_warning(
                    f"{case_prefix}.expected_success",
                    "Expected success not specified",
                )

    def _validate_mcp_skill(self, spec: ToolSpec, result: ValidationResult) -> None:
        """Validate MCP and SKILL configuration."""
        # MCP validation
        if spec.mcp and spec.mcp.enabled:
            if not spec.mcp.transport:
                result.add_warning(
                    "mcp.transport",
                    "MCP enabled but transport type not specified",
                )

        # SKILL validation
        if spec.skill and spec.skill.enabled:
            if not spec.skill.category:
                result.add_warning(
                    "skill.category",
                    "SKILL enabled but category not specified",
                )

    def _validate_parameters(self, spec: ToolSpec, result: ValidationResult) -> None:
        """Validate parameter definitions."""
        if not spec.parameters:
            result.add_warning("parameters", "Tool has no parameters defined")
            return

        param_names = set()
        for i, param in enumerate(spec.parameters):
            param_prefix = f"parameters[{i}]"

            if not param.name:
                result.add_error(f"{param_prefix}.name", "Parameter name is required")

            if param.name in param_names:
                result.add_error(f"{param_prefix}.name", f"Duplicate parameter name: {param.name}")

            param_names.add(param.name)

            if not param.type:
                result.add_error(f"{param_prefix}.type", "Parameter type is required")

            if not param.description:
                result.add_warning(f"{param_prefix}.description", "Parameter description is empty")


def validate_spec(spec: ToolSpec) -> ValidationResult:
    """
    Convenience function to validate a ToolSpec.

    Returns ValidationResult with errors and warnings.
    """
    validator = SpecValidator()
    return validator.validate(spec)
