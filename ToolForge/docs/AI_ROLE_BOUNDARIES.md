# AI Role Boundaries in ToolForge

This document defines the strict boundaries for AI assistance in ToolForge. AI is an **assistant** to human operators, not a replacement for deterministic validation, testing, safety checks, or user approval.

## Core Principles

1. **AI assists, does not replace** - AI helps generate and suggest, but never bypasses human oversight
2. **Fail closed on uncertainty** - When AI output is ambiguous or invalid, fail rather than guess
3. **Deterministic validation is mandatory** - All AI-generated code must pass static analysis, tests, and security checks
4. **User approval is required** - No autonomous deployments or modifications without explicit user consent
5. **Local-first security** - AI operates within local sandbox boundaries; no remote execution or data exfiltration

## Allowed AI Responsibilities

### Spec Generation
- Convert natural language prompts to structured ToolSpec YAML
- Suggest parameter types, descriptions, and examples
- Recommend appropriate security settings (with human review)
- Propose test cases and evaluation criteria

### Code Suggestions
- Generate tool implementation code from specs
- Suggest test implementations
- Provide documentation and README content
- Recommend MCP/SKILL integration patterns

### Validation Assistance
- Analyze validation errors and suggest fixes
- Provide prompt refinement suggestions based on validation failures
- Explain security concerns and mitigation strategies
- Recommend best practices for tool design

## Forbidden AI Responsibilities

### File System Operations
- **FORBIDDEN**: AI must not autonomously write files to disk
- **FORBIDDEN**: AI must not autonomously delete or modify existing files
- **FORBIDDEN**: AI must not autonomously execute file system operations
- **ALLOWED**: AI may generate file content as text for user review and approval

### Command Execution
- **FORBIDDEN**: AI must not autonomously execute shell commands
- **FORBIDDEN**: AI must not autonomously run subprocesses
- **FORBIDDEN**: AI must not autonomously install dependencies or packages
- **ALLOWED**: AI may suggest commands for user to execute

### Deployment Actions
- **FORBIDDEN**: AI must not autonomously deploy tools to production
- **FORBIDDEN**: AI must not autonomously publish packages
- **FORBIDDEN**: AI must not autonomously modify CI/CD configurations
- **ALLOWED**: AI may generate deployment scripts for user review

### Bypassing Validation
- **FORBIDDEN**: AI must not suggest disabling tests or validation
- **FORBIDDEN**: AI must not suggest bypassing security checks
- **FORBIDDEN**: AI must not suggest reducing test coverage
- **FORBIDDEN**: AI must not suggest ignoring type checking or linting errors

### Direct Network Access
- **FORBIDDEN**: AI must not autonomously make HTTP requests
- **FORBIDDEN**: AI must not autonomously fetch remote resources
- **FORBIDDEN**: AI must not autonomously connect to external APIs
- **ALLOWED**: AI may generate code that makes network requests when explicitly requested by user

## Implementation Boundaries

### AI Spec Generator (`packages/ai/spec_generator.py`)
- **Input**: Natural language prompt, optional constraints
- **Output**: Structured ToolSpec object (not YAML file)
- **Validation**: Must pass SpecValidator before being used
- **Fallback**: Must fall back to rule-based generation on failure
- **No file writes**: Returns data structures only; CLI handles file I/O

### AI Providers (`packages/ai/providers.py`)
- **Interface**: `AIProvider.complete_json()` returns structured data
- **Timeout**: All API calls must have configurable timeouts
- **Retry**: Must implement exponential backoff retry logic
- **Mock**: Must provide MockProvider for CI testing without network calls
- **Error handling**: Must fail gracefully when provider unavailable

### CLI Integration (`apps/cli/toolforge_cli/main.py`)
- **User approval**: All AI-generated specs require user confirmation before scaffolding
- **Fallback**: CLI must work without AI (rule-based generation always available)
- **Graceful degradation**: If AI provider fails, fall back to rule-based without error
- **Optional dependencies**: AI features are optional extras; core works without them

## Safety Guarantees

### Path Traversal Protection
- AI-generated specs must include explicit path restrictions
- Default to empty `allowed_read_paths` and `allowed_write_paths`
- User must explicitly approve any path access

### Capability Restrictions
- AI must not suggest enabling shell execution by default
- AI must not suggest enabling network access by default
- AI must not suggest enabling database access without explicit user request
- All capabilities require explicit user approval in the spec

### Test Coverage
- AI-generated tools must include tests
- AI must not suggest reducing test coverage below baseline
- All generated code must pass existing test suite
- Eval harness is mandatory for all tools

## Enforcement Mechanisms

### Code-Level
- Type hints and validation on all AI output
- Pydantic models enforce schema constraints
- SpecValidator validates all AI-generated specs before use
- TestValidator ensures generated code passes tests

### Process-Level
- User approval required before scaffolding AI-generated tools
- CI runs with MockProvider to prevent external API calls
- All AI features are optional extras in pyproject.toml
- Core functionality works without AI dependencies

### Documentation-Level
- All AI-related functions include docstrings explaining boundaries
- Code comments reinforce "no autonomous action" constraints
- This document serves as canonical reference for AI role boundaries

## Future Considerations

### AI-Augmented Testing (Phase 7+)
- AI may suggest additional test cases based on code analysis
- AI may generate edge case scenarios
- AI must not replace deterministic test requirements
- All AI-suggested tests require human review

### AI-Assisted Debugging (Phase 8+)
- AI may analyze error logs and suggest fixes
- AI must not autonomously apply fixes
- AI must not suggest disabling error handling
- All AI suggestions require user approval

### AI Memory/Registry (Phase 10+)
- AI may maintain context across sessions
- AI must not persist sensitive information without consent
- AI memory is optional and can be disabled
- All AI memory is local-first and encrypted

## Compliance Checklist

Before merging AI-related features:

- [ ] All AI output passes SpecValidator
- [ ] All AI-generated code passes TestValidator
- [ ] All AI-generated code passes type checking (mypy)
- [ ] All AI-generated code passes linting (ruff)
- [ ] CI uses MockProvider for all tests
- [ ] User approval is required for all AI-generated content
- [ ] Fallback to rule-based generation works without AI
- [ ] AI features are optional extras in pyproject.toml
- [ ] Documentation reflects AI role boundaries
- [ ] No autonomous file writes or command execution
- [ ] Path traversal protection is enforced
- [ ] Capability restrictions are enforced
- [ ] Test coverage requirements are met

## References

- [AI Spec Generator Documentation](AI_SPEC_GENERATOR.md)
- [ToolForge Architecture](ARCHITECTURE.md)
- [Security Policy](../configs/security_policy.yaml)
- [Model Policy](../configs/model_policy.yaml)
