# ToolForge Architecture

## Overview

ToolForge is a CLI-first, general-purpose **Tool Creator Platform**. Given a natural-language prompt (or an existing spec), it scaffolds, validates, runs, and packages tools — each optionally exposed as an MCP server, a Copilot Skill, and an evaluation harness.

```
toolforge new tool --from-prompt "Create a tool that cleans CSV files"
toolforge generate mcp csv-cleaner
toolforge generate skill csv-cleaner
toolforge eval csv-cleaner
toolforge package csv-cleaner
```

---

## Directory Layout

```
ToolForge/
├── apps/
│   ├── cli/          # Click CLI entry point
│   └── web/          # Web UI (placeholder)
├── packages/
│   ├── core/         # ToolSpec, generators, registry, package builder, spec-from-prompt
│   ├── runners/      # sandbox_runner, tool_runner, eval_runner
│   ├── templates/    # Jinja2 templates (MCP server, skill, eval, readme, docker)
│   ├── validators/   # Schema, security, MCP, skill, test validators
│   └── integrations/ # agent_skills importer + toolathlon bridges
├── tools/
│   ├── examples/     # Working example tools (csv-cleaner, json-schema-validator, local-file-hasher)
│   └── generated/    # CLI-generated tools land here (git-ignored)
├── skills/generated/ # Generated SKILL.md files
├── evals/generated/  # Generated eval harnesses
├── dist/             # Packaged .zip archives
├── tests/            # Unit tests (pytest)
├── docs/             # This directory
└── toolforge/        # Package entrypoint and metadata
```

---

## Core Packages

### `packages/core/tool_spec.py`

Pydantic v2 model hierarchy representing a complete tool definition:

```
ToolSpec
├── parameters: list[ParameterSpec]
├── output: OutputSpec
├── security: SecuritySpec
├── eval: EvalSpec
│   ├── cases: list[EvalCase]
│   └── criteria: list[EvalCriterion]
├── mcp: MCPSpec
└── skill: SkillSpec
```

Key enums: `ToolLanguage`, `SandboxLevel`, `PrivacyLevel`, `ToolCapability`, `EvalCriterionType`.

### `packages/core/spec_from_prompt.py`

Converts a natural-language prompt into a `ToolSpec`.

```
SpecGeneratorProvider (ABC)
├── RuleBasedSpecGenerator  — regex + keyword heuristics, no LLM required
└── LLMSpecGenerator        — OpenAI / Anthropic structured output
```

### Generators (`packages/core/`)

| Module | Output |
|--------|--------|
| `tool_generator.py` | Scaffolded tool dir with `toolforge.yaml`, `tool.py`, `README.md`, tests |
| `mcp_generator.py` | MCP server (Python or TypeScript) + `Dockerfile` |
| `skill_generator.py` | `SKILL.md` under `skills/{category}/{slug}/` |
| `eval_generator.py` | `task_config.json` + `cases/` + `evaluation.py` |
| `doc_generator.py` | `README.md` |

### `packages/core/registry.py`

Flat-file JSON registry (`toolforge_registry.json`) in workspace root. Operations: `register`, `deregister`, `find`, `list_all`, `search_by_tag`.

### `packages/core/package_builder.py`

Produces `{slug}-{version}.zip` containing `manifest.json` + tool sources.

---

## Runners (`packages/runners/`)

```
SandboxResult  ← sandbox_runner.run_in_sandbox()
ToolRunResult  ← tool_runner.run_tool()
EvalReport     ← eval_runner.run_evals()
```

### Sandbox Levels

| Level | Isolation |
|-------|-----------|
| 0 | Direct subprocess (no isolation) |
| 1 | Env isolation (secrets stripped) |
| 2 | Timeout + env isolation (default) |
| 3 | Docker `--network=none --cpus=0.5 --memory=128m` |
| 4 | Docker read-only filesystem |

Tool inputs are passed via `TOOLFORGE_INPUTS` environment variable (JSON-serialised dict) — never on the command line.

---

## Validators (`packages/validators/`)

Run in order by `toolforge validate <slug>`:

1. **schema_validator** — YAML structure + Pydantic v2 validation
2. **security_validator** — policy enforcement (network, file access, sandbox level)
3. **mcp_validator** — server.py syntax check via `py_compile`
4. **skill_validator** — required SKILL.md sections + frontmatter keys
5. **test_validator** — runs `pytest` with `--json-report`

---

## Integrations (`packages/integrations/`)

### `agent_skills/importer.py`

Copies a legacy SKILL.md into the ToolForge workspace, inferring category from the directory structure.

### `toolathlon/`

| Module | Purpose |
|--------|---------|
| `task_adapter.py` | Converts toolathlon task JSON → `EvalCase` objects |
| `config_bridge.py` | Maps toolathlon MCP server YAML → `ToolSpec` |
| `runner_bridge.py` | Runs toolathlon tasks through ToolForge eval runner |

---

## Data Flow

```
Prompt
  │
  ▼
spec_from_prompt  →  ToolSpec  →  scaffold_tool  →  tools/generated/{slug}/
                                       │
                          ┌────────────┼────────────┐
                          ▼            ▼             ▼
                    generate_mcp  generate_skill  generate_eval
                          │            │             │
                    MCP server     SKILL.md      eval harness
                          │
                     validate  →  run_tool  →  run_evals
                                                    │
                                              package  →  dist/{slug}-{version}.zip
```

---

## Security Design

**ToolForge provides process isolation and resource controls for local development, not cryptographic or hostile-code-safe sandboxing.**

- **No shell injection**: inputs passed via env var, not CLI args
- **Secret stripping**: env vars matching `*_KEY`, `*_SECRET`, `*_TOKEN`, `*_PASSWORD`, etc. are stripped before subprocess
- **Safety analyzer**: scans tool source for hardcoded secrets, path traversal, `os.system`/`subprocess` calls, and denied imports
- **Sandbox levels**: progressively tighter Docker isolation for local execution risks:
  - Level 0: Direct subprocess (no isolation; for trusted code only)
  - Level 1: Env stripping + secret filtering
  - Level 2: Process timeout + env isolation (default; safe for development)
  - Level 3: Docker with network disabled, CPU/memory limits
  - Level 4: Docker with read-only filesystem and seccomp
- **Limitations**: Sandbox isolation is NOT designed to contain hostile code, execute untrusted user input, or provide data isolation between runs. For production untrusted-code execution, use VM-level or container-level isolation (Firecracker, gVisor, Kata Containers).
- Rigorous security testing has not been performed; this is suitable for trusted developer environments only.
