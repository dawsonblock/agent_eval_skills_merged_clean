<div align="center">

# Agent Eval & Skills Platform

**A unified workspace for building and evaluating AI agent tools.**

[![Python](https://img.shields.io/badge/Python-3.9%2B-3776AB?logo=python&logoColor=white)](https://python.org)
[![Node.js](https://img.shields.io/badge/Node.js-18%2B-339933?logo=node.js&logoColor=white)](https://nodejs.org)
[![MCP](https://img.shields.io/badge/MCP-Protocol-6B46C1)](https://modelcontextprotocol.io)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker&logoColor=white)](https://docker.com)
[![License: Apache--2.0](https://img.shields.io/badge/License-Apache--2.0-22c55e)](LICENSE)

[ToolForge](#-toolforge) · [Agent Skills](#-agent-skills) · [Toolathlon GYM](#-toolathlon-gym) · [Getting Started](#-getting-started) · [Architecture](#-architecture)

</div>

---

## Overview

This repository is a controlled-merge of three interconnected systems designed for end-to-end AI agent development: from authoring tools to evaluating agents against real-world task benchmarks.

| Component | Purpose | Scale |
|-----------|---------|-------|
| [**ToolForge**](ToolForge/) | Create, validate, package, and deploy AI tools as MCP servers and Copilot Skills | CLI platform |
| [**Agent Skills**](agent-skills-curated/) | Curated registry of reusable agent skills with built-in evaluation | 10+ production skills |
| [**Toolathlon GYM**](toolathlon-gym-curated/) | Self-contained benchmark environment for evaluating LLM agents on real-world tasks | 503 tasks · 25 MCP servers |

---

## ToolForge

> **CLI-first platform for creating, validating, running, and packaging AI tools.**

ToolForge turns a natural-language description into a structured prototype tool with an MCP server, skill file, evaluation harness, and packaged `.zip` artifact for local development workflows.

```bash
# Turn a prompt into a complete tool scaffold
toolforge new tool --from-prompt "Create a tool that cleans CSV files"

# Generate MCP server + Copilot Skill wrappers
toolforge generate mcp   csv-cleaner
toolforge generate skill csv-cleaner

# Validate against all policy checks
toolforge validate csv-cleaner

# Run the tool locally with sandboxing
toolforge run csv-cleaner --input input_path=examples/input.csv

# Evaluate against the generated test harness
toolforge eval csv-cleaner

# Package for distribution
toolforge package csv-cleaner
# → dist/csv-cleaner-0.1.0.zip
```

### Features

- **Spec-from-prompt** — Natural language → structured `ToolSpec` via rule-based inference or LLM (OpenAI/Anthropic)
- **Full scaffolding** — Generates `tool.py`, `toolforge.yaml`, `README.md`, and a pytest test suite
- **MCP server generation** — Python (`mcp>=1.10.1`) or TypeScript (`@modelcontextprotocol/sdk`)
- **Copilot Skill generation** — Ready-to-use `SKILL.md` files generated with tool-local packaging support
- **Evaluation harness** — `task_config.json`, per-case JSON files, and automated scoring
- **Five validators** — schema, security, MCP, skill, and test validators in one command
- **Safety analyzer** — Static scan for hardcoded secrets, path traversal, and dangerous system calls
- **Progressive sandboxing** — Docker isolation levels 0–4 for untrusted tool execution
- **Registry** — Flat-file JSON registry for local tool discovery and management
- **Integrations** — Import legacy Copilot Skills and Toolathlon GYM task configs

### Installation

```bash
cd ToolForge
pip install -e ".[dev]"
```

### Project Structure

```
ToolForge/
├── apps/cli/                  # Click-based CLI (toolforge command)
├── packages/
│   ├── core/                  # ToolSpec models, generators, registry, packager
│   ├── runners/               # Sandbox runner, tool runner, eval runner
│   ├── templates/             # Jinja2 scaffolding templates
│   ├── validators/            # Schema, security, MCP, skill, test validators
│   └── integrations/          # Agent Skills + Toolathlon bridges
├── tools/
│   ├── examples/              # csv-cleaner, json-schema-validator, local-file-hasher
│   └── generated/             # CLI-generated tools (git-ignored)
├── skills/generated/          # Legacy/global skill outputs (optional)
├── evals/generated/           # Legacy/global eval outputs (optional)
└── docs/                      # ARCHITECTURE, CLI_REFERENCE, TOOL_SPEC, VALIDATORS
```

### Documentation

| Document | Description |
|----------|-------------|
| [ARCHITECTURE.md](ToolForge/docs/ARCHITECTURE.md) | System design, data flow, security model |
| [CLI_REFERENCE.md](ToolForge/docs/CLI_REFERENCE.md) | Full `toolforge` command reference |
| [TOOL_SPEC.md](ToolForge/docs/TOOL_SPEC.md) | `toolforge.yaml` field reference |
| [GENERATORS.md](ToolForge/docs/GENERATORS.md) | Generator API reference |
| [VALIDATORS.md](ToolForge/docs/VALIDATORS.md) | Validator API reference |
| [INTEGRATIONS.md](ToolForge/docs/INTEGRATIONS.md) | Agent Skills and Toolathlon bridges |

### Security

- Inputs passed via `TOOLFORGE_INPUTS` env var — no shell injection through CLI args
- Credential env vars (`*_KEY`, `*_SECRET`, `*_TOKEN`, `*_PASSWORD`) stripped before subprocess execution
- Static safety analysis on every generated tool
- Includes path-safety and static safety checks, but generated tools still require human review and additional hardening before sensitive or production use.

---

## Agent Skills

> **Curated registry of reusable agent skills with structured evaluation.**

A collection of high-quality skill definitions for AI coding agents, organized by category. Each skill ships with a `SKILL.md` instruction file, evaluation scripts, and reference materials — following the [Agent Skills](https://agentskills.io/) format.

### Available Skills

#### Coding Agents & IDEs

| Skill | Description |
|-------|-------------|
| [`mcp-builder`](agent-skills-curated/skills/coding-agents-and-ides/mcp-builder/) | Build MCP servers in Python (FastMCP) or TypeScript. Includes planning workflows, MCP best-practices, and evaluation scripts |
| [`skill-creator`](agent-skills-curated/skills/coding-agents-and-ides/skill-creator/) | Author, evaluate, and benchmark `SKILL.md` files. Covers bundling, eval runs, and performance measurement |

#### Web & Frontend Development

| Skill | Description |
|-------|-------------|
| [`frontend-design`](agent-skills-curated/skills/web-and-frontend-development/frontend-design/) | Generate distinctive frontend interfaces with intentional design direction — avoids generic AI aesthetics |
| [`web-artifacts-builder`](agent-skills-curated/skills/web-and-frontend-development/web-artifacts-builder/) | Build multi-component HTML artifacts with React, Tailwind CSS, and shadcn/ui |
| [`excalidraw`](agent-skills-curated/skills/web-and-frontend-development/excalidraw/) | Generate valid `.excalidraw` architecture diagrams from codebase analysis |

#### PDF & Documents

| Skill | Description |
|-------|-------------|
| [`pdf`](agent-skills-curated/skills/pdf-and-documents/pdf/) | Extract, parse, and work with PDF documents |
| [`docx`](agent-skills-curated/skills/pdf-and-documents/docx/) | Read and write Word documents programmatically |
| [`xlsx`](agent-skills-curated/skills/pdf-and-documents/xlsx/) | Read and write Excel workbooks programmatically |
| [`pptx`](agent-skills-curated/skills/pdf-and-documents/pptx/) | Read and write PowerPoint presentations programmatically |

#### Browser & Automation

| Skill | Description |
|-------|-------------|
| [`webapp-testing`](agent-skills-curated/skills/browser-and-automation/webapp-testing/) | Test local web apps with Playwright — verify UI behavior, capture screenshots, view browser logs |

### CLI & Evaluation

```bash
cd agent-skills-curated
npm install

# List available skills
node bin/cli.js list

# Run evaluations
node evals/evaluate.js --skill mcp-builder
```

### Structure

```
agent-skills-curated/
├── bin/cli.js                 # Skill CLI
├── evals/
│   ├── evaluate.js            # Evaluation runner
│   ├── scorer.js              # Scoring logic
│   ├── scenarios/             # Evaluation scenarios
│   ├── rubrics/               # Scoring rubrics
│   └── judges/                # LLM judge configs
└── skills/
    ├── coding-agents-and-ides/
    ├── web-and-frontend-development/
    ├── pdf-and-documents/
    └── browser-and-automation/
```

---

## Toolathlon GYM

> **503-task self-contained benchmark environment for evaluating LLM agents on real-world tool use.**

Training and evaluating LLM agents on real-world tool use is hard. Most datasets are too narrow, too small, or require live external APIs. Toolathlon GYM provides 503 multi-step tasks backed by a local PostgreSQL database and 25 MCP servers — no external API calls required at runtime.

Built on and extending [Toolathlon](https://github.com/hkust-nlp/Toolathlon) by HKUST-NLP, this environment applies the same format at a substantially larger and more diverse scale.

### What Makes It Different

- **503 tasks** across real-world enterprise domains: HR, sales, finance, research, e-commerce, education
- **25 local MCP servers** covering CRM, spreadsheets, calendars, forms, databases, email, and more
- **Self-contained** — PostgreSQL database seeded from `db/init.sql.gz`, no external services
- **Fully automated** — preprocess → agent run → evaluate, no human graders
- **Long-horizon** — tasks require multi-step planning across heterogeneous tools under a fixed step budget
- **Docker-native** — fresh ephemeral container per task, parallel execution supported

### Task Domains

| Domain | Example Tasks |
|--------|--------------|
| **Salesforce CRM** | Sales forecasting, HR attrition, support SLA audits, territory analysis |
| **WooCommerce** | Inventory management, coupon analysis, customer lifetime value, shipping audits |
| **Yahoo Finance** | Portfolio analysis, sector rotation, earnings reports, dividend tracking |
| **Canvas LMS** | Grade distribution, assignment workload, enrollment analytics, quiz analysis |
| **Arxiv / Research** | Literature reviews, citation networks, conference preparation, grant proposals |
| **HowToCook** | Meal planning, nutrition analysis, event catering, wellness tracking |
| **Google Workspace** | Sheets, Forms, Calendar, Docs — cross-system data sync |
| **Notion** | Knowledge bases, project tracking, team wikis |
| **YouTube** | Transcript analysis, channel benchmarking, content planning |
| **12306 (Rail)** | Chinese rail travel planning for multi-city business trips |
| **Playwright** | Competitor pricing scraping, review sentiment, market research |

### Quick Start

**Prerequisites:** Docker and Docker Compose

```bash
cd toolathlon-gym-curated

# Build and start PostgreSQL
docker compose up -d postgres

# Run a single task (spawns a fresh ephemeral container)
MODEL_PLATFORM=openai_compatible \
MODEL_NAME=claude-sonnet-4-5 \
MODEL_API_KEY=sk-xxx \
MODEL_API_URL=https://api.example.com/v1 \
bash scripts/run_containerized.sh howtocook-meal-plan-gcal

# Run tasks in parallel
bash run_parallel.sh --workers 4

# Verify setup
bash scripts/test_containerized.sh
```

Task output is written to `dumps/<task>/<timestamp>/`. Full conversation trajectories and per-turn LLM logs are included.

### MCP Servers

The 25 bundled MCP servers cover:

| Category | Servers |
|----------|---------|
| **Data & Spreadsheets** | Excel, Google Sheets, PDF tools |
| **Productivity** | Notion, Google Forms, Google Calendar |
| **Communication** | Email (SMTP/IMAP) |
| **Development** | CLI, Filesystem, Playwright |
| **Domain-specific** | Salesforce, WooCommerce, Yahoo Finance, Canvas LMS, Arxiv, HowToCook, YouTube, 12306, Scholarly |

### Structure

```
toolathlon-gym-curated/
├── tasks/finalpool/           # 503 task definitions
├── local_servers/             # 25 local MCP server implementations
├── configs/                   # Global config, model/session keys
├── db/                        # PostgreSQL seed data
├── utils/                     # API clients, conversation helpers, eval utilities
├── scripts/                   # Run, test, and containerized execution scripts
└── explorer/                  # Web UI for browsing tasks
```

### Safety Note

Toolathlon's terminal-style MCP tooling is powerful. **Only run it inside disposable Docker containers or restricted sandboxes.** Do not point it at your real filesystem, production database, or legal evidence store.

---

## Getting Started

### Prerequisites

| Tool | Version |
|------|---------|
| Python | 3.9+ |
| Node.js | 18+ |
| Docker | 24+ |
| Docker Compose | v2+ |

### Clone and Set Up

```bash
git clone https://github.com/dawsonblock/agent_eval_skills_merged_clean.git
cd agent_eval_skills_merged_clean

# ToolForge
cd ToolForge && pip install -e ".[dev]" && cd ..

# Agent Skills CLI
cd agent-skills-curated && npm install && cd ..

# Toolathlon GYM (Docker)
cd toolathlon-gym-curated && docker compose up -d postgres && cd ..
```

### Suggested Placement

Keep this repository under a dedicated `labs/`, `agents/`, or `tooling/` directory. Do not embed it directly into production application code.

---

## Architecture

```
agent_eval_skills_merged_clean/
│
├── ToolForge/                     # Tool creation + packaging platform
│   ├── apps/cli/                  # CLI entry point
│   ├── packages/core/             # ToolSpec, spec-from-prompt, tool generator
│   ├── packages/validators/       # Schema, security, MCP, skill, test validators
│   ├── packages/runners/          # Sandbox, tool, and eval runners
│   └── packages/integrations/     # Bridges to agent-skills + toolathlon
│
├── agent-skills-curated/          # Reusable skill registry
│   ├── skills/                    # Skill definitions by category
│   └── evals/                     # Evaluation framework
│
└── toolathlon-gym-curated/        # Agent benchmark environment
    ├── tasks/finalpool/           # 503 benchmark tasks
    ├── local_servers/             # 25 MCP server implementations
    └── utils/                     # Shared evaluation + agent utilities
```

The three components are designed to compose:

1. **ToolForge** creates a new tool and generates its MCP server
2. **Agent Skills** wraps it as a reusable skill with evaluation rubrics
3. **Toolathlon GYM** exercises agents that use that tool in realistic multi-step task scenarios

---

## License

[MIT](LICENSE) — see individual component directories for any additional license files.

---

<div align="center">
<sub>Built for controlled agent development. Pin this in your own repo and review updates before pulling.</sub>
</div>
