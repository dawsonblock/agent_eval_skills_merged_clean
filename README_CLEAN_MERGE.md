# Agent Eval + Skills Clean Merge

This package is a cleaned merge of two uploaded repositories:

1. `toolathlon_gym-main.zip` -> `toolathlon-gym-curated/`
2. `agent-skills-main 3.zip` -> `agent-skills-curated/`

## Purpose

Use this as controlled infrastructure for agent development:

- `toolathlon-gym-curated/` is the benchmark/evaluation lab.
- `agent-skills-curated/` is the reusable skill/instruction registry.

Validation status: release candidate for controlled testing only when validation evidence artifacts are present for the target environment.

Evidence artifacts:

- Unified summary JSON: [.validation_logs/validation_summary.json](.validation_logs/validation_summary.json)
- Toolathlon preflight JSON: [.validation_logs/toolathlon_preflight_summary.json](.validation_logs/toolathlon_preflight_summary.json)
- Phase logs: [.validation_logs/](.validation_logs/)

Current gate status:

```text
ZIP extraction ................ ✅ Verified
ZIP cache cleanliness ......... ✅ Verified
Python syntax ................. ✅ Verified
Agent Skills .................. ✅ Verified
ToolForge doctor .............. 🟡 Passes after dependency setup
ToolForge full validation ..... ✅ Passes with grouped tests on supported Python
Toolathlon fresh preflight .... ✅ Passes after artifact build
Toolathlon artifact builder ... ✅ Completes with per-package timeouts
Docker validation ............. ✅ Build + in-container preflight pass
Unified validation ............ ✅ Passing in current environment
Release readiness ............. ✅ Release candidate (controlled testing)
```

Promotion rule outcome is evidence-gated. If required evidence files are missing or show non-passing required gates, downgrade classification to strong repair candidate. This is not a production security certification.

Do not drop this directly into production application code. Keep it under a `labs/`, `agents/`, or separate tooling repo.

## What was kept

### Toolathlon-GYM

Kept the benchmark runner, task definitions, preprocess/evaluation scripts, MCP server code, Docker files, database seed, configs, utilities, and explorer.

### Agent Skills

Kept the CLI, evaluator scripts, root docs, and all 23 agent skills:

**Coding & IDE Integration (3 skills)**
- coding-agents-and-ides/mcp-builder
- coding-agents-and-ides/mintlify-docs-updater
- coding-agents-and-ides/skill-creator

**Browser Automation (1 skill)**
- browser-and-automation/webapp-testing

**Communication (1 skill)**
- communication/internal-comms

**Image & Video Generation (5 skills)**
- image-and-video-generation/algorithmic-art
- image-and-video-generation/canvas-design
- image-and-video-generation/instagram-reel-editor
- image-and-video-generation/remotion
- image-and-video-generation/slack-gif-creator

**Marketing & Sales (2 skills)**
- marketing-and-sales/humanizer
- marketing-and-sales/instagram-posting

**PDF & Documents (5 skills)**
- pdf-and-documents/doc-coauthoring
- pdf-and-documents/docx
- pdf-and-documents/pdf
- pdf-and-documents/pptx
- pdf-and-documents/xlsx

**Productivity & Tasks (1 skill)**
- productivity-and-tasks/pm-skills

**Web & Frontend Development (5 skills)**
- web-and-frontend-development/brand-guidelines
- web-and-frontend-development/excalidraw
- web-and-frontend-development/frontend-design
- web-and-frontend-development/theme-factory
- web-and-frontend-development/web-artifacts-builder

## What was removed

Removed material that is unnecessary or undesirable for your current direction:

- demo videos and GIFs
- documentation screenshots and visual assets
- Python/Node cache folders
- common local run outputs such as dumps, benchmark logs, results, and outputs
- root sample output spreadsheet
- DXT/demo assets

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
