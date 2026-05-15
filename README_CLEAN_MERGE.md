# Agent Eval + Skills Clean Merge

This package is a cleaned merge of two uploaded repositories:

1. `toolathlon_gym-main.zip` -> `toolathlon-gym-curated/`
2. `agent-skills-main 3.zip` -> `agent-skills-curated/`

## Purpose

Use this as controlled infrastructure for agent development:

- `toolathlon-gym-curated/` is the benchmark/evaluation lab.
- `agent-skills-curated/` is the reusable skill/instruction registry.

Do not drop this directly into production application code. Keep it under a `labs/`, `agents/`, or separate tooling repo.

## What was kept

### Toolathlon-GYM

Kept the benchmark runner, task definitions, preprocess/evaluation scripts, MCP server code, Docker files, database seed, configs, utilities, and explorer.

### Agent Skills

Kept the CLI, evaluator scripts, root docs, and these higher-value skills:

- coding-agents-and-ides/mcp-builder
- coding-agents-and-ides/skill-creator
- browser-and-automation/webapp-testing
- pdf-and-documents/pdf
- pdf-and-documents/docx
- pdf-and-documents/xlsx
- pdf-and-documents/pptx
- web-and-frontend-development/excalidraw
- web-and-frontend-development/frontend-design
- web-and-frontend-development/web-artifacts-builder

## What was removed

Removed material that is unnecessary or undesirable for your current direction:

- demo videos and GIFs
- bundled generated skill package ZIPs
- marketing/social/media-specific agent skills
- image/video generation skills
- bundled font files
- GitHub workflow metadata
- Python/Node cache folders
- common local run outputs such as dumps, benchmark logs, results, and outputs
- root sample output spreadsheet
- DXT/demo assets and visual documentation images where not needed for code execution

## Safety notes

Toolathlon's terminal-style MCP tooling is useful for evaluation, but should only run inside disposable Docker containers or restricted sandboxes. Do not point it at your real filesystem, legal evidence store, or production repo.

Agent Skills still includes upstream CLI behavior. Pin this package in your own repo and avoid blind remote auto-updates unless you intentionally fork and control the update source.

## Suggested placement

```text
JUDGE_ATLASX/
  agents/
    skills/              # copy/customize from agent-skills-curated
  labs/
    toolathlon_gym/      # copy/use toolathlon-gym-curated
    judgeathlon_gym/     # your future custom legal/evidence benchmark suite
```
