"""
Tests for AI Spec Generator components.

Tests cover:
- AISpecGenerator facade class
- Validation pipeline
- Prompt refinement suggestions
- Provider implementations (mocked)
"""
from __future__ import annotations

import pytest

from packages.ai.prompt_refiner import PromptRefiner, suggest_prompt_improvements
from packages.ai.spec_generator import AISpecGenerator
from packages.ai.validation import Severity, ValidationError, ValidationResult, validate_spec
from packages.core.spec_from_prompt import RuleBasedSpecGenerator
from packages.core.tool_spec import ToolSpec


class TestValidationPipeline:
    """Tests for the validation pipeline."""

    def test_validate_valid_spec(self) -> None:
        """Test validation of a valid spec."""
        generator = RuleBasedSpecGenerator()
        spec = generator.generate("Create a CSV cleaner tool")

        result = validate_spec(spec)
        assert result.is_valid
        assert len(result.errors) == 0

    def test_validate_missing_name(self) -> None:
        """Test validation catches missing name."""
        # Create a spec with missing name - use model_construct to bypass pydantic validation
        # since we want to test our validation logic, not pydantic's
        from packages.core.tool_spec import SecuritySpec, PrivacyLevel

        spec = ToolSpec.model_construct(
            name="",
            slug="test-tool",
            version="1.0.0",
            description="Test tool",
            language="python",
            entry_point="tool.py",
            parameters=[],
            security=SecuritySpec(
                requires_filesystem=False,
                requires_network=False,
                required_capabilities=[],
                allowed_read_paths=[],
                allowed_write_paths=[],
                allowed_extensions=[],
                max_file_size_mb=50,
                privacy_level=PrivacyLevel.INTERNAL,
            ),
            mcp=None,
            skill=None,
            eval=None,
        )

        result = validate_spec(spec)
        assert not result.is_valid
        assert any(e.field == "name" for e in result.errors)

    def test_validate_missing_slug(self) -> None:
        """Test validation catches missing slug."""
        from packages.core.tool_spec import SecuritySpec, PrivacyLevel

        spec = ToolSpec.model_construct(
            name="Test Tool",
            slug="",
            version="1.0.0",
            description="Test tool",
            language="python",
            entry_point="tool.py",
            parameters=[],
            security=SecuritySpec(
                requires_filesystem=False,
                requires_network=False,
                required_capabilities=[],
                allowed_read_paths=[],
                allowed_write_paths=[],
                allowed_extensions=[],
                max_file_size_mb=50,
                privacy_level=PrivacyLevel.INTERNAL,
            ),
            mcp=None,
            skill=None,
            eval=None,
        )

        result = validate_spec(spec)
        assert not result.is_valid
        assert any(e.field == "slug" for e in result.errors)

    def test_validate_security_paths(self) -> None:
        """Test validation checks security path configuration."""
        from packages.core.tool_spec import SecuritySpec, PrivacyLevel

        spec = ToolSpec.model_construct(
            name="Test Tool",
            slug="test-tool",
            version="1.0.0",
            description="Test tool",
            language="python",
            entry_point="tool.py",
            parameters=[],
            security=SecuritySpec(
                requires_filesystem=True,
                requires_network=False,
                required_capabilities=[],
                allowed_read_paths=[],
                allowed_write_paths=[],
                allowed_extensions=[],
                max_file_size_mb=50,
                privacy_level=PrivacyLevel.INTERNAL,
            ),
            mcp=None,
            skill=None,
            eval=None,
        )

        result = validate_spec(spec)
        # Should have warnings about missing paths
        assert result.has_warnings()
        assert any("allowed_read_paths" in w.field for w in result.warnings)


class TestPromptRefiner:
    """Tests for prompt refinement suggestions."""

    def test_suggest_for_missing_name(self) -> None:
        """Test suggestions for missing name error."""
        refiner = PromptRefiner()
        error = ValidationError(field="name", message="Tool name cannot be empty", severity=Severity.ERROR)
        result = ValidationResult(is_valid=False, errors=[error], warnings=[])

        suggestions = refiner.suggest_improvements("Create a tool", result)
        assert any("name" in s.lower() for s in suggestions)

    def test_suggest_for_short_prompt(self) -> None:
        """Test suggestions for short prompts."""
        refiner = PromptRefiner()
        result = ValidationResult(is_valid=True, errors=[], warnings=[])

        suggestions = refiner.suggest_improvements("Tool", result)
        assert any("short" in s.lower() or "detail" in s.lower() for s in suggestions)

    def test_suggest_for_missing_parameters(self) -> None:
        """Test suggestions for missing parameters."""
        refiner = PromptRefiner()
        result = ValidationResult(is_valid=True, errors=[], warnings=[])

        suggestions = refiner.suggest_improvements("Create a tool that processes data", result)
        assert any("parameter" in s.lower() or "input" in s.lower() for s in suggestions)

    def test_convenience_function(self) -> None:
        """Test the convenience function."""
        result = ValidationResult(is_valid=True, errors=[], warnings=[])
        suggestions = suggest_prompt_improvements("Create a tool", result)
        assert isinstance(suggestions, list)


class TestAISpecGenerator:
    """Tests for AISpecGenerator facade."""

    def test_rule_based_provider(self) -> None:
        """Test rule-based provider works."""
        generator = AISpecGenerator(provider="rule_based")
        spec = generator.generate("Create a CSV cleaner tool")

        assert spec is not None
        assert spec.slug == "csv-cleaner"

    def test_fallback_to_rule_based(self) -> None:
        """Test fallback to rule-based on provider failure."""
        # Use a provider that will fail (e.g., openai without API key)
        generator = AISpecGenerator(provider="openai", fallback_to_rule_based=True)

        # This should fallback to rule-based since OPENAI_API_KEY is not set
        spec = generator.generate("Create a CSV cleaner tool")

        assert spec is not None

    def test_validation_integration(self) -> None:
        """Test validation is integrated into generation."""
        generator = AISpecGenerator(provider="rule_based")
        spec = generator.generate("Create a CSV cleaner tool")

        # Should not raise validation errors for valid spec
        assert spec is not None

    def test_invalid_provider(self) -> None:
        """Test invalid provider raises error."""
        generator = AISpecGenerator(provider="invalid_provider", fallback_to_rule_based=False)

        with pytest.raises(ValueError, match="Unknown provider"):
            generator.generate("Create a tool")


class TestOllamaSpecGenerator:
    """Tests for OllamaSpecGenerator (without actual Ollama connection)."""

    def test_initialization(self) -> None:
        """Test Ollama generator can be initialized."""
        from packages.ai.providers.ollama_generator import OllamaSpecGenerator

        generator = OllamaSpecGenerator(model="llama3", base_url="http://localhost:11434")
        assert generator._model == "llama3"
        assert generator._base_url == "http://localhost:11434"


class TestAzureOpenAISpecGenerator:
    """Tests for AzureOpenAISpecGenerator (without actual Azure connection)."""

    def test_missing_endpoint_raises_error(self) -> None:
        """Test missing endpoint raises error during initialization."""
        with pytest.raises(ValueError, match="azure_openai_endpoint is required"):
            AISpecGenerator(
                provider="azure_openai",
                azure_openai_deployment="test-deployment",
                fallback_to_rule_based=False,
            )
