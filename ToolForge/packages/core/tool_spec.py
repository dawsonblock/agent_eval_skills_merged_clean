"""
ToolForge core data model — ToolSpec and all sub-models.

A ToolSpec is the authoritative declaration of a tool.  It is stored as
``toolforge.yaml`` inside each tool directory.  Everything the platform
does — generation, validation, sandbox execution, MCP wrapping, skill
generation, eval generation, and packaging — is driven from this spec.
"""
from __future__ import annotations

import json
import re
from enum import Enum
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------

class ToolLanguage(str, Enum):
    PYTHON = "python"
    TYPESCRIPT = "typescript"
    BASH = "bash"


class SandboxLevel(int, Enum):
    NONE = 0
    ENV_ISOLATION = 1
    SUBPROCESS_TIMEOUT = 2
    DOCKER_NETWORK = 3
    DOCKER_NO_NETWORK = 4


class PrivacyLevel(str, Enum):
    PUBLIC = "public"
    INTERNAL = "internal"
    SENSITIVE = "sensitive"
    EVIDENCE_GRADE = "evidence-grade"


class ToolCapability(str, Enum):
    READ_FILES = "read_files"
    WRITE_FILES = "write_files"
    CALL_HTTP = "call_http"
    EXECUTE_CODE = "execute_code"
    RUN_SHELL = "run_shell"
    CALL_DATABASE = "call_database"
    MANIPULATE_DATA = "manipulate_data"


class EvalCriterionType(str, Enum):
    NO_ERROR = "no_error"
    CONTAINS = "contains"
    EXACT_MATCH = "exact_match"
    REGEX_MATCH = "regex_match"
    JSON_SCHEMA = "json_schema"
    PERFORMANCE = "performance"
    SEMANTIC_SIMILARITY = "semantic_similarity"
    CUSTOM_SCRIPT = "custom_script"


# ---------------------------------------------------------------------------
# Parameter models
# ---------------------------------------------------------------------------

class ParameterSpec(BaseModel):
    """Declares a single input parameter for a tool."""

    name: str = Field(..., description="Parameter name (snake_case)")
    type: str = Field(..., description="JSON-Schema primitive: string | number | integer | boolean | array | object")
    description: str = Field(..., description="Human-readable description for the LLM / user")
    required: bool = Field(True, description="Whether this parameter is required")
    default: Any = Field(None, description="Default value (only when required=false)")
    enum: list[Any] | None = Field(None, description="Allowed values")
    min_length: int | None = Field(None, description="For string parameters")
    max_length: int | None = Field(None, description="For string parameters")
    minimum: float | None = Field(None, description="For numeric parameters")
    maximum: float | None = Field(None, description="For numeric parameters")
    examples: list[Any] = Field(default_factory=list, description="Example values")

    @field_validator("name")
    @classmethod
    def _snake_case(cls, v: str) -> str:
        if not re.match(r"^[a-z][a-z0-9_]*$", v):
            raise ValueError(f"Parameter name must be snake_case, got: {v!r}")
        return v

    @field_validator("type")
    @classmethod
    def _valid_type(cls, v: str) -> str:
        allowed = {"string", "number", "integer", "boolean", "array", "object"}
        if v not in allowed:
            raise ValueError(f"Parameter type must be one of {allowed}, got: {v!r}")
        return v


class OutputSpec(BaseModel):
    """Declares the output contract of a tool."""

    type: str = Field(..., description="JSON-Schema type of the primary output")
    description: str = Field("", description="Human-readable description of the output")
    schema: dict[str, Any] | None = Field(None, description="Full JSON Schema for structured outputs")
    examples: list[Any] = Field(default_factory=list, description="Example outputs")


# ---------------------------------------------------------------------------
# Security model
# ---------------------------------------------------------------------------

class SecuritySpec(BaseModel):
    """Declares required capabilities and resource constraints for sandboxing."""

    required_capabilities: list[ToolCapability] = Field(
        default_factory=list,
        description="Capabilities the tool needs; drives minimum sandbox level",
    )
    requires_network: bool = Field(False, description="Tool needs outbound network access")
    requires_shell: bool = Field(False, description="Tool needs shell/subprocess execution")
    requires_filesystem: bool = Field(False, description="Tool needs filesystem write access")
    
    # File access patterns (replaces generic allowed_paths)
    allowed_read_paths: list[str] = Field(
        default_factory=list,
        description="Filesystem paths the tool is allowed to read (glob patterns OK)",
    )
    allowed_write_paths: list[str] = Field(
        default_factory=list,
        description="Filesystem paths the tool is allowed to write (glob patterns OK)",
    )
    blocked_paths: list[str] = Field(
        default_factory=lambda: [
            "~/.ssh/**", "~/.aws/**", "~/.config/**",
            "/etc/**", "/var/**", "/root/**",
        ],
        description="Filesystem paths blocked regardless of tool permissions",
    )
    
    # File constraints
    allowed_extensions: list[str] = Field(
        default_factory=list,
        description="File extensions allowed (e.g. ['.csv', '.json']); empty = all allowed",
    )
    max_file_size_mb: int = Field(50, ge=1, description="Maximum file size in MB")
    allow_symlinks: bool = Field(False, description="Allow reading/following symlinks")
    
    # Network constraints
    allowed_domains: list[str] = Field(
        default_factory=list,
        description="Domains tool is allowed to contact; empty = block all",
    )
    blocked_domains: list[str] = Field(
        default_factory=list,
        description="Domains explicitly blocked",
    )
    
    # Command execution constraints
    allowed_commands: list[str] = Field(
        default_factory=list,
        description="Commands allowed via subprocess; empty = only safe defaults",
    )
    blocked_commands: list[str] = Field(
        default_factory=lambda: [
            "rm", "sudo", "chmod", "chown", "curl", "wget",
            "ssh", "scp", "kubectl", "docker", "aws",
        ],
        description="Commands explicitly blocked",
    )
    
    # Resource limits
    max_memory_mb: int | None = Field(None, ge=1, description="Memory ceiling; None = no limit")
    max_cpu_seconds: int | None = Field(None, ge=1, description="CPU time ceiling; None = uses global timeout")
    
    # Metadata
    privacy_level: PrivacyLevel = Field(PrivacyLevel.INTERNAL, description="Data sensitivity level")
    approved_by: str | None = Field(None, description="Identity that reviewed and approved security posture")
    
    @model_validator(mode="before")
    @classmethod
    def _parse_legacy_fields(cls, data: dict) -> dict:
        """Translate legacy security fields to new format with deprecation warning."""
        if isinstance(data, dict):
            # Legacy allow_file_read/write → requires_filesystem + paths
            if "allow_file_read" in data:
                import warnings
                warnings.warn(
                    "security.allow_file_read is deprecated; use requires_filesystem and allowed_read_paths",
                    DeprecationWarning,
                    stacklevel=2
                )
                if data.pop("allow_file_read"):
                    data["requires_filesystem"] = True
            
            if "allow_file_write" in data:
                import warnings
                warnings.warn(
                    "security.allow_file_write is deprecated; use requires_filesystem and allowed_write_paths",
                    DeprecationWarning,
                    stacklevel=2
                )
                if data.pop("allow_file_write"):
                    data["requires_filesystem"] = True
            
            # Legacy allow_network → requires_network
            if "allow_network" in data:
                data["requires_network"] = data.pop("allow_network")
        
        return data


# ---------------------------------------------------------------------------
# Eval criterion
# ---------------------------------------------------------------------------

class EvalCriterion(BaseModel):
    """A single acceptance criterion used when evaluating tool outputs."""

    name: str
    type: EvalCriterionType
    description: str = ""
    target: Any = Field(None, description="Expected value / pattern / schema / threshold")
    weight: float = Field(1.0, ge=0.0, description="Relative importance (higher = more important)")
    max_duration_ms: float | None = Field(None, description="Max duration in ms (for PERFORMANCE criterion)")
    script_path: str | None = Field(None, description="Relative path to evaluator script (custom_script type)")

    @field_validator("name")
    @classmethod
    def _non_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Eval criterion name must not be empty")
        return v


# ---------------------------------------------------------------------------
# Eval spec
# ---------------------------------------------------------------------------

class EvalCase(BaseModel):
    """A single eval test case (input → expected)."""

    id: str
    description: str = ""
    inputs: dict[str, Any] = Field(default_factory=dict)
    expected_output: Any = None
    criteria: list[EvalCriterion] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)


class EvalSpec(BaseModel):
    """Bundled eval configuration for a tool."""

    enabled: bool = Field(True, description="Whether eval is enabled")
    criteria: list[EvalCriterion] = Field(default_factory=list, description="Global criteria applied to all cases")
    cases: list[EvalCase] = Field(default_factory=list)
    baseline_pass_rate: float = Field(0.8, ge=0.0, le=1.0, description="Minimum fraction of cases that must pass")
    judge_provider: str = Field("rule_based", description="How to judge complex criteria (rule_based | openai | anthropic)")


# ---------------------------------------------------------------------------
# MCP spec
# ---------------------------------------------------------------------------

class MCPSpec(BaseModel):
    """Describes how this tool is exposed as an MCP server tool."""

    enabled: bool = Field(True)
    tool_name: str | None = Field(None, description="Override the MCP tool name (defaults to tool slug)")
    description_override: str | None = Field(None, description="Override description shown in MCP tool listing")
    server_name: str | None = Field(None, description="MCP server name (defaults to tool slug + '-server')")
    server_language: ToolLanguage = Field(ToolLanguage.PYTHON, description="Language for generated MCP server")
    transport: Literal["stdio", "http"] = Field("stdio")
    port: int | None = Field(None, description="HTTP transport port (only when transport=http)")


# ---------------------------------------------------------------------------
# Skill spec
# ---------------------------------------------------------------------------

class SkillSpec(BaseModel):
    """Describes how this tool is wrapped as an agent skill (SKILL.md)."""

    enabled: bool = Field(True)
    category: str = Field("general", description="Skill category directory (e.g. data-processing)")
    when_to_use: list[str] = Field(
        default_factory=list,
        description="List of trigger phrases for the WHEN: section of SKILL.md",
    )
    not_when: list[str] = Field(
        default_factory=list,
        description="List of counter-trigger phrases for the DO NOT USE FOR section",
    )


# ---------------------------------------------------------------------------
# Primary ToolSpec
# ---------------------------------------------------------------------------

class ToolSpec(BaseModel):
    """
    Authoritative spec for a ToolForge tool.
    Stored as ``toolforge.yaml`` in the tool directory.
    """

    # --- Identity ---
    name: str = Field(..., description="Human-readable name, e.g. 'CSV Cleaner'")
    slug: str = Field(..., description="Kebab-case identifier, e.g. 'csv-cleaner'")
    version: str = Field("0.1.0", description="Semantic version")
    description: str = Field(..., description="One-sentence description for LLM context")
    long_description: str = Field("", description="Multi-paragraph description for docs/README")
    tags: list[str] = Field(default_factory=list, description="Searchable tags")
    author: str = Field("", description="Author name or email")

    # --- Implementation ---
    language: ToolLanguage = Field(ToolLanguage.PYTHON)
    entry_point: str = Field(
        "tool.py",
        description="Relative path to the primary implementation file",
    )
    dependencies: list[str] = Field(
        default_factory=list,
        description="pip/npm packages required (no version pinning required)",
    )

    # --- Interface ---
    parameters: list[ParameterSpec] = Field(
        default_factory=list,
        description="Input parameters (order defines CLI arg order)",
    )
    output: OutputSpec = Field(
        default_factory=lambda: OutputSpec(type="string", description="Tool output"),
        description="Output type declaration",
    )

    # --- Security ---
    security: SecuritySpec = Field(default_factory=SecuritySpec)
    sandbox_level: SandboxLevel = Field(SandboxLevel.SUBPROCESS_TIMEOUT)

    # --- MCP wrapping ---
    mcp: MCPSpec = Field(default_factory=MCPSpec)

    # --- Agent skill ---
    skill: SkillSpec = Field(default_factory=SkillSpec)

    # --- Eval ---
    eval: EvalSpec = Field(default_factory=EvalSpec)

    # --- Metadata ---
    created_at: str | None = Field(None, description="ISO-8601 creation timestamp (set by toolforge)")
    source_prompt: str | None = Field(
        None,
        description="The original natural-language prompt used to generate this spec (spec-from-prompt only)",
    )

    # ------------------------------------------------------------------
    # Validators
    # ------------------------------------------------------------------

    @field_validator("slug")
    @classmethod
    def _slug_format(cls, v: str) -> str:
        if not re.match(r"^[a-z][a-z0-9-]*$", v):
            raise ValueError(f"slug must be kebab-case (e.g. 'csv-cleaner'), got: {v!r}")
        return v

    @field_validator("version")
    @classmethod
    def _semver(cls, v: str) -> str:
        if not re.match(r"^\d+\.\d+\.\d+", v):
            raise ValueError(f"version must be semver (e.g. 0.1.0), got: {v!r}")
        return v

    @model_validator(mode="after")
    def _sandbox_level_vs_capabilities(self) -> "ToolSpec":
        """Ensure sandbox_level is sufficient for declared capabilities."""
        min_level = 0
        if ToolCapability.CALL_HTTP in self.security.required_capabilities:
            min_level = max(min_level, 1)
        if ToolCapability.WRITE_FILES in self.security.required_capabilities:
            min_level = max(min_level, 1)
        if ToolCapability.EXECUTE_CODE in self.security.required_capabilities:
            min_level = max(min_level, 2)
        if ToolCapability.RUN_SHELL in self.security.required_capabilities:
            min_level = max(min_level, 2)
        if ToolCapability.CALL_DATABASE in self.security.required_capabilities:
            min_level = max(min_level, 2)
        if self.sandbox_level < min_level:
            raise ValueError(
                f"sandbox_level={self.sandbox_level} is too low for capabilities "
                f"{self.security.required_capabilities}; minimum required: {min_level}"
            )
        return self

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def required_params(self) -> list[ParameterSpec]:
        return [p for p in self.parameters if p.required]

    def optional_params(self) -> list[ParameterSpec]:
        return [p for p in self.parameters if not p.required]

    def to_json_schema_inputs(self) -> dict[str, Any]:
        """Generate a JSON Schema object describing the tool's input parameters."""
        properties: dict[str, Any] = {}
        required: list[str] = []
        for p in self.parameters:
            prop: dict[str, Any] = {"type": p.type, "description": p.description}
            if p.enum is not None:
                prop["enum"] = p.enum
            if p.examples:
                prop["examples"] = p.examples
            if p.type == "string":
                if p.min_length is not None:
                    prop["minLength"] = p.min_length
                if p.max_length is not None:
                    prop["maxLength"] = p.max_length
            if p.type in ("number", "integer"):
                if p.minimum is not None:
                    prop["minimum"] = p.minimum
                if p.maximum is not None:
                    prop["maximum"] = p.maximum
            if p.default is not None:
                prop["default"] = p.default
            properties[p.name] = prop
            if p.required:
                required.append(p.name)
        schema: dict[str, Any] = {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "type": "object",
            "properties": properties,
        }
        if required:
            schema["required"] = required
        return schema

    @classmethod
    def from_yaml(cls, path: Path) -> "ToolSpec":
        """Load a ToolSpec from a toolforge.yaml file."""
        from ruamel.yaml import YAML  # local import to keep top-level lean

        yaml = YAML(typ="safe")
        with open(path, "r") as fh:
            data = yaml.load(fh)
        return cls.model_validate(data or {})

    def to_yaml(self, path: Path) -> None:
        """Persist this ToolSpec as toolforge.yaml (round-trip safe)."""
        from ruamel.yaml import YAML

        yaml = YAML()
        yaml.default_flow_style = False
        yaml.width = 10_000
        data = json.loads(self.model_dump_json(exclude_none=True))
        with open(path, "w") as fh:
            yaml.dump(data, fh)
