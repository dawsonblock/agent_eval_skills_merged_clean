# ToolForge

**ToolForge** is a CLI-first prototype for creating, validating, running, and packaging AI tools — each optionally exposed as an MCP server, a Copilot Skill, and a reproducible evaluation harness.

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
- **Copilot Skill generation** — ready-to-use `SKILL.md` files with tool-local packaging support
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

`toolforge eval` reads tool-local eval case files from `tools/generated/<slug>/evals/cases/*.json` when present. If those files are missing, it falls back to `eval.cases` in `toolforge.yaml`.

### Package

```bash
toolforge package local-file-hasher
# → dist/local-file-hasher-0.1.0.zip
```

### Local DeepSeek Tool UI Demo

```bash
cd ToolForge
python -m pip install -e ".[demo]"
cp .env.example .env
# Set DEEPSEEK_API_KEY in .env for live model responses
./run_local_deepseek_demo.sh
```

Demo URL: `http://127.0.0.1:8080`

The demo provides:

- Local chat UI with configurable DeepSeek model string
- Tool registry browsing and permission preview
- Two-step tool run flow (`preview` then explicit `approve`)
- Tool planning/creation/validation under `generated_tools/`
- Local output viewer for generated artifacts

---

## Example Tools

Three working example tools ship with ToolForge:

| Tool | Description |
| --- | --- |
| [`csv-cleaner`](tools/examples/csv-cleaner/) | Strips whitespace, removes blank rows, deduplicates CSV files |
| [`json-schema-validator`](tools/examples/json-schema-validator/) | Validates JSON data against a JSON Schema (Draft 7) |
| [`local-file-hasher`](tools/examples/local-file-hasher/) | Computes MD5/SHA-256/SHA-512 hashes of local files |

---

## Project Structure

```text
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
├── skills/generated/          # Optional legacy/global generated SKILL.md files
├── evals/generated/           # Optional legacy/global generated eval harnesses
├── dist/                      # Packaged .zip archives
├── tests/                     # Package-level unit tests (pytest)
├── docs/                      # Documentation
└── toolforge/                 # Package entrypoint and module metadata
```

---

## Documentation

| Document | Description |
| --- | --- |
| [ARCHITECTURE.md](docs/ARCHITECTURE.md) | System design, data flow, security model |
| [CLI_REFERENCE.md](docs/CLI_REFERENCE.md) | Every `toolforge` command |
| [TOOL_SPEC.md](docs/TOOL_SPEC.md) | `toolforge.yaml` field reference |
| [GENERATORS.md](docs/GENERATORS.md) | Generator API reference |
| [VALIDATORS.md](docs/VALIDATORS.md) | Validator API reference |
| [INTEGRATIONS.md](docs/INTEGRATIONS.md) | Agent Skills and Toolathlon bridges |

---

## Testing

```bash
# Install dev dependencies first
python -m pip install -e ".[dev]"

# Run all package-level tests
pytest tests/ -v

# Run SkillForge AI tests explicitly
PYTHONPATH=. pytest -q tests/test_skillforge_ai

# Run a specific example tool's tests
cd tools/examples/csv-cleaner && pytest tests/ -v
```

---

## License

Apache-2.0
