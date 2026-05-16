# ToolForge

**ToolForge** is a CLI-first platform for creating, validating, running, and packaging AI tools — each optionally exposed as an MCP server, a Copilot Skill, and a reproducible evaluation harness.

```bash
toolforge new tool --from-prompt "Create a tool that cleans CSV files"
toolforge generate mcp  csv-cleaner
toolforge generate skill csv-cleaner
toolforge eval           csv-cleaner
toolforge package        csv-cleaner
```

---

## Features

- **Spec-from-prompt** — turn a natural-language description into a fully-structured `ToolSpec`
- **Scaffolding** — generates `tool.py`, `toolforge.yaml`, `README.md`, and a pytest test suite
- **MCP server generation** — Python (`mcp>=1.10.1`) or TypeScript (`@modelcontextprotocol/sdk`)
- **Copilot Skill generation** — ready-to-use `SKILL.md` files under the correct category directory
- **Evaluation harness** — `task_config.json`, per-case JSON files, and scoring logic
- **Validators** — schema, security, MCP, skill, and test validators in a single `toolforge validate` command
- **Safety analyzer** — static scan for hardcoded secrets, path traversal, and shell execution
- **Packaging** — reproducible `.zip` archives with `manifest.json`
- **Registry** — flat-file JSON registry for local tool discovery
- **Integrations** — import legacy Copilot Skills and Toolathlon Gym task configs

---

## Quick Start

### Install

```bash
# From source (editable)
cd ToolForge
pip install -e ".[dev]"
```

### Initialise a workspace

```bash
toolforge init
```

### Create a tool

```bash
toolforge new tool --from-prompt "Create a tool that hashes local files"
```

### Generate MCP server and Skill

```bash
toolforge generate mcp   local-file-hasher
toolforge generate skill local-file-hasher
```

### Validate

```bash
toolforge validate local-file-hasher
```

### Run

```bash
toolforge run local-file-hasher --input file_path=README.md
```

### Evaluate

```bash
toolforge eval local-file-hasher
```

### Package

```bash
toolforge package local-file-hasher
# → dist/local-file-hasher-0.1.0.zip
```

---

## Example Tools

Three working example tools ship with ToolForge:

| Tool | Description |
|------|-------------|
| [`csv-cleaner`](tools/examples/csv-cleaner/) | Strips whitespace, removes blank rows, deduplicates CSV files |
| [`json-schema-validator`](tools/examples/json-schema-validator/) | Validates JSON data against a JSON Schema (Draft 7) |
| [`local-file-hasher`](tools/examples/local-file-hasher/) | Computes MD5/SHA-256/SHA-512 hashes of local files |

---

## Project Structure

```
ToolForge/
├── apps/cli/                  # Click CLI entry point
├── packages/
│   ├── core/                  # ToolSpec, generators, registry, package_builder
│   ├── runners/               # sandbox_runner, tool_runner, eval_runner
│   ├── templates/             # Jinja2 templates
│   ├── validators/            # All validators
│   └── integrations/          # agent_skills + toolathlon bridges
├── tools/
│   ├── examples/              # csv-cleaner, json-schema-validator, local-file-hasher
│   └── generated/             # CLI-generated tools (git-ignored)
├── skills/generated/          # Generated SKILL.md files
├── evals/generated/           # Generated eval harnesses
├── dist/                      # Packaged .zip archives
├── tests/                     # Package-level unit tests (pytest)
├── docs/                      # Documentation
└── legacy/                    # Imported source repos (git submodules or copies)
```

---

## Documentation

| Document | Description |
|----------|-------------|
| [ARCHITECTURE.md](docs/ARCHITECTURE.md) | System design, data flow, security model |
| [CLI_REFERENCE.md](docs/CLI_REFERENCE.md) | Every `toolforge` command |
| [TOOL_SPEC.md](docs/TOOL_SPEC.md) | `toolforge.yaml` field reference |
| [GENERATORS.md](docs/GENERATORS.md) | Generator API reference |
| [VALIDATORS.md](docs/VALIDATORS.md) | Validator API reference |
| [INTEGRATIONS.md](docs/INTEGRATIONS.md) | Agent Skills and Toolathlon bridges |

---

## Testing

```bash
# Run all package-level tests
pytest tests/ -v

# Run a specific example tool's tests
cd tools/examples/csv-cleaner && pytest tests/ -v
```

---

## License

MIT
