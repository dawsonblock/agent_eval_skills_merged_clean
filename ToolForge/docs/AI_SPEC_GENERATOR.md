# AI Spec Generator

The AI Spec Generator is a controlled AI integration that converts natural language prompts into structured ToolForge tool specifications (toolforge.yaml). It supports multiple AI providers and includes robust validation, retry logic, and fallback mechanisms.

## Overview

The AI Spec Generator is designed as a safe, reliable layer on top of ToolForge's deterministic generator. It:

- Generates strict toolforge.yaml specs without direct file writes or command execution
- Preserves the deterministic pipeline for generation, validation, testing, and evaluation
- Supports multiple AI providers (OpenAI, Anthropic, Ollama, Azure OpenAI)
- Includes comprehensive validation before returning specs
- Provides automatic fallback to rule-based generation on AI failures
- Offers prompt refinement suggestions for validation errors

## Usage

### CLI Command: `toolforge ai spec`

Generate a tool spec from a natural-language prompt:

```bash
# Basic usage with rule-based provider (default)
toolforge ai spec --prompt "Create a CSV cleaner tool"

# Use OpenAI
toolforge ai spec --prompt "Create a JSON schema validator" \
  --provider openai \
  --model gpt-4o

# Use Anthropic
toolforge ai spec --prompt "Create a file hasher tool" \
  --provider anthropic \
  --model claude-3-haiku-20240307

# Use Ollama (local model)
toolforge ai spec --prompt "Create a web scraper tool" \
  --provider ollama \
  --model llama3

# Output to stdout instead of file
toolforge ai spec --prompt "Create a tool" --stdout

# Interactive mode: review spec before writing
toolforge ai spec --prompt "Create a tool" --interactive

# Dry run: generate without writing files
toolforge ai spec --prompt "Create a tool" --dry-run

# Configure retry and timeout
toolforge ai spec --prompt "Create a tool" \
  --max-retries 5 \
  --timeout 60

# Enable automatic fallback to rule-based
toolforge ai spec --prompt "Create a tool" \
  --provider openai \
  --fallback-to-rule-based
```

### Enhanced `new tool` Command

The existing `toolforge new tool` command now supports AI providers with additional flags:

```bash
# Use AI provider with review mode
toolforge new tool --from-prompt "Create a CSV cleaner tool" \
  --provider openai \
  --review

# Enable fallback to rule-based
toolforge new tool --from-prompt "Create a tool" \
  --provider anthropic \
  --fallback-to-rule-based

# Configure retry settings
toolforge new tool --from-prompt "Create a tool" \
  --provider openai \
  --max-retries 3 \
  --timeout 30
```

### Python API

Use the AISpecGenerator as an importable module:

```python
from packages.ai.spec_generator import AISpecGenerator

# Create generator
gen = AISpecGenerator(
    provider="openai",
    model="gpt-4o",
    max_retries=3,
    timeout_seconds=30,
    fallback_to_rule_based=True,
)

# Generate spec
spec = gen.generate("Create a CSV cleaner tool")

# Access spec properties
print(spec.name)
print(spec.slug)
print(spec.to_yaml())
```

## Supported Providers

### OpenAI

Requires `openai` package and `OPENAI_API_KEY` environment variable:

```bash
pip install openai
export OPENAI_API_KEY="sk-..."
```

Default model: `gpt-4o-mini`

### Anthropic

Requires `anthropic` package and `ANTHROPIC_API_KEY` environment variable:

```bash
pip install anthropic
export ANTHROPIC_API_KEY="sk-ant-..."
```

Default model: `claude-3-haiku-20240307`

### Ollama (Local Models)

Requires Ollama running locally and `requests` package:

```bash
# Install Ollama
curl https://ollama.ai/install.sh | sh

# Pull a model
ollama pull llama3

# Start Ollama server
ollama serve

# Install requests
pip install requests
```

Default model: `llama3`

### Azure OpenAI

Requires `openai` package and `AZURE_OPENAI_API_KEY` environment variable:

```bash
pip install openai
export AZURE_OPENAI_API_KEY="..."
```

Configuration requires endpoint and deployment name via CLI flags or config.

## Configuration

Add to `ToolForge/configs/toolforge.yaml`:

```yaml
ai:
  spec_generator:
    provider: rule_based  # rule_based | openai | anthropic | ollama | azure_openai
    model: null  # Override default model
    timeout_seconds: 30
    max_retries: 3
    retry_backoff_seconds: 1
    fallback_to_rule_based: true
    interactive: false
    ollama_base_url: "http://localhost:11434"
    azure_openai:
      endpoint: null  # Azure OpenAI endpoint URL
      deployment: null  # Azure OpenAI deployment name
      api_version: "2024-02-15-preview"
```

## Validation Pipeline

The AI Spec Generator includes a comprehensive validation pipeline that checks:

- **Structural validation**: Required fields (name, slug, version, language, entry_point)
- **Security validation**: Path patterns, file size limits, privacy levels
- **Eval validation**: Test cases, criteria, pass rates
- **MCP/SKILL validation**: Required fields for MCP and SKILL configurations
- **Parameter validation**: Parameter names, types, descriptions

If validation fails, the generator can:
1. Raise a ValueError with detailed error messages
2. Automatically fallback to rule-based generation (if enabled)
3. Provide prompt refinement suggestions

## Error Handling

### Retry Logic

Transient errors (timeouts, rate limits) trigger automatic retry with exponential backoff:

- Default: 3 retries
- Backoff: 1s, 2s, 4s (configurable)
- Non-retryable errors: authentication, invalid prompts

### Fallback Mechanism

When AI generation fails, the system can automatically fallback to rule-based generation:

- Enabled by default via `--fallback-to-rule-based` flag
- Logs fallback reason for transparency
- Preserves original prompt in spec metadata

### Prompt Refinement

On validation failure, the system provides specific suggestions to improve the prompt:

```python
from packages.ai.prompt_refiner import suggest_prompt_improvements
from packages.ai.validation import validate_spec

spec = gen.generate("Create a tool")
validation_result = validate_spec(spec)

if not validation_result.is_valid:
    suggestions = suggest_prompt_improvements(prompt, validation_result)
    for suggestion in suggestions:
        print(f"- {suggestion}")
```

## Architecture

The AI Spec Generator follows a layered architecture:

```
User Prompt
    ↓
AISpecGenerator (facade)
    ↓
Provider (OpenAI/Anthropic/Ollama/Azure OpenAI/Rule-based)
    ↓
Validation Pipeline
    ↓
ToolSpec
```

Key components:

- **AISpecGenerator**: Unified facade for all providers with retry and fallback
- **LLMSpecGenerator**: Enhanced OpenAI/Anthropic support with retry logic
- **OllamaSpecGenerator**: Local model support via Ollama API
- **AzureOpenAISpecGenerator**: Azure OpenAI integration
- **RuleBasedSpecGenerator**: Keyword/heuristic extraction (fallback)
- **SpecValidator**: Comprehensive validation pipeline
- **PromptRefiner**: Prompt improvement suggestions

## Design Principles

1. **Safety First**: AI does not write files or execute commands directly
2. **Deterministic Pipeline**: AI only generates specs; deterministic generator handles scaffolding
3. **Validation First**: All specs validated before use
4. **Graceful Degradation**: Automatic fallback to rule-based on failures
5. **Configurable**: All behavior configurable via flags and config
6. **Transparent**: Clear error messages and logging

## Testing

Run the AI spec generator tests:

```bash
# Run all AI tests
pytest ToolForge/tests/test_ai_spec_generator.py -v

# Run specific test class
pytest ToolForge/tests/test_ai_spec_generator.py::TestValidationPipeline -v
```

## Troubleshooting

### OpenAI API Key Not Set

```
ValueError: OPENAI_API_KEY environment variable not set.
```

Solution: Set the environment variable:
```bash
export OPENAI_API_KEY="sk-..."
```

### Anthropic API Key Not Set

```
ValueError: ANTHROPIC_API_KEY environment variable not set.
```

Solution: Set the environment variable:
```bash
export ANTHROPIC_API_KEY="sk-ant-..."
```

### Ollama Connection Failed

```
requests.exceptions.ConnectionError: Failed to establish connection
```

Solution: Ensure Ollama server is running:
```bash
ollama serve
```

### Azure OpenAI Missing Configuration

```
ValueError: azure_openai_endpoint required for azure_openai provider
```

Solution: Provide endpoint and deployment:
```bash
toolforge ai spec --provider azure_openai \
  --azure-openai-endpoint "https://..." \
  --azure-openai-deployment "..."
```

### Validation Failed

```
ValueError: Generated spec failed validation:
name: Tool name cannot be empty
```

Solution: Improve your prompt with more specific details, or enable fallback to rule-based.

## Future Enhancements

Potential future improvements:

- Streaming responses for better UX
- Few-shot learning with example specs
- Custom example sets via config
- Additional AI providers (e.g., local models via llama.cpp)
- Prompt templates for common tool types
- Integration with external prompt engineering tools
