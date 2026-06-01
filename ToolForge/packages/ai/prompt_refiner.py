"""
Prompt Refiner — provides suggestions for improving natural-language prompts.

Analyzes validation errors and warnings to suggest prompt improvements.

IMPORTANT: AI ROLE BOUNDARIES
- This refiner only provides suggestions; does not autonomously modify prompts
- All suggestions require user review and approval
- No autonomous file writes or command execution
- See ToolForge/docs/AI_ROLE_BOUNDARIES.md for full boundaries
"""

from __future__ import annotations

from packages.ai.validation import ValidationResult, ValidationError


class PromptRefiner:
    """Analyzes validation errors and suggests prompt improvements."""

    def suggest_improvements(self, prompt: str, validation_result: ValidationResult) -> list[str]:
        """
        Generate suggestions for improving the prompt based on validation errors.

        Args:
            prompt: Original natural-language prompt
            validation_result: ValidationResult from spec validation

        Returns:
            List of improvement suggestions
        """
        suggestions: list[str] = []

        # Analyze errors and generate suggestions
        for error in validation_result.errors:
            suggestions.extend(self._suggest_for_error(error, prompt))

        # Analyze warnings and generate suggestions
        for warning in validation_result.warnings:
            suggestions.extend(self._suggest_for_warning(warning, prompt))

        # General suggestions based on prompt analysis
        suggestions.extend(self._general_suggestions(prompt, validation_result))

        return suggestions

    def _suggest_for_error(self, error: ValidationError, prompt: str) -> list[str]:
        """Generate suggestions for a specific validation error."""
        suggestions: list[str] = []

        if error.field == "name":
            suggestions.append(
                "Specify a clear tool name in your prompt, e.g., 'Create a tool named CSV Cleaner that...'"
            )

        if error.field == "slug":
            suggestions.append(
                "The tool slug was not properly generated. Try being more specific about the tool's purpose."
            )

        if error.field == "description":
            suggestions.append(
                "Add a brief description of what the tool does and its primary use case."
            )

        if error.field == "version":
            suggestions.append("Specify a version for the tool (e.g., 'version 1.0.0').")

        if error.field == "language":
            suggestions.append(
                "Specify the programming language (e.g., 'Python tool' or 'TypeScript tool')."
            )

        if error.field == "entry_point":
            suggestions.append("Specify the entry point file (e.g., 'tool.py' or 'index.ts').")

        if error.field.startswith("security"):
            if "allowed_read_paths" in error.field:
                suggestions.append(
                    "Specify which directories the tool should be able to read from (e.g., './examples/**')."
                )
            if "allowed_write_paths" in error.field:
                suggestions.append(
                    "Specify which directories the tool should be able to write to (e.g., './outputs/**')."
                )

        if error.field.startswith("eval"):
            suggestions.append(
                "Include specific test cases in your prompt, describing expected inputs and outputs."
            )

        if error.field.startswith("parameters"):
            if "name" in error.field:
                suggestions.append(
                    "Clearly specify the parameters the tool should accept, including their names."
                )
            if "type" in error.field:
                suggestions.append(
                    "Specify the data types for each parameter (e.g., string, integer, boolean)."
                )
            if "description" in error.field:
                suggestions.append("Add descriptions for each parameter explaining what they do.")

        return suggestions

    def _suggest_for_warning(self, warning: ValidationError, prompt: str) -> list[str]:
        """Generate suggestions for a specific validation warning."""
        suggestions: list[str] = []

        if warning.field == "description":
            suggestions.append(
                "Consider adding a more detailed description of the tool's purpose and use cases."
            )

        if warning.field == "security.privacy_level":
            suggestions.append("Specify the privacy level for the tool (e.g., INTERNAL, PUBLIC).")

        if warning.field == "eval":
            suggestions.append(
                "Consider adding an eval harness with test cases to validate the tool's behavior."
            )

        if warning.field == "mcp.transport":
            suggestions.append(
                "If you want MCP support, specify the transport type (e.g., 'stdio' or 'http')."
            )

        if warning.field == "skill.category":
            suggestions.append(
                "Specify the skill category (e.g., 'file-processing', 'web-and-automation')."
            )

        if warning.field == "parameters":
            suggestions.append("Consider adding more parameters to make the tool more flexible.")

        return suggestions

    def _general_suggestions(self, prompt: str, validation_result: ValidationResult) -> list[str]:
        """Generate general suggestions based on prompt analysis."""
        suggestions: list[str] = []

        # Check prompt length
        if len(prompt) < 50:
            suggestions.append(
                "Your prompt is quite short. Provide more details about the tool's purpose, inputs, outputs, and behavior."
            )

        # Check for common missing elements
        prompt_lower = prompt.lower()

        if "parameter" not in prompt_lower and "input" not in prompt_lower:
            suggestions.append(
                "Your prompt doesn't mention parameters or inputs. Specify what the tool should accept as input."
            )

        if "output" not in prompt_lower and "return" not in prompt_lower:
            suggestions.append(
                "Your prompt doesn't mention outputs. Specify what the tool should produce."
            )

        if "test" not in prompt_lower and "example" not in prompt_lower:
            suggestions.append(
                "Consider including example use cases or test scenarios in your prompt."
            )

        # Check for security-related keywords
        if any(kw in prompt_lower for kw in ["file", "read", "write", "network", "http"]):
            if "security" not in prompt_lower and "permission" not in prompt_lower:
                suggestions.append(
                    "Your tool may need file or network access. Specify security requirements and allowed paths."
                )

        return suggestions


def suggest_prompt_improvements(prompt: str, validation_result: ValidationResult) -> list[str]:
    """
    Convenience function to get prompt improvement suggestions.

    Args:
        prompt: Original natural-language prompt
        validation_result: ValidationResult from spec validation

    Returns:
        List of improvement suggestions
    """
    refiner = PromptRefiner()
    return refiner.suggest_improvements(prompt, validation_result)
