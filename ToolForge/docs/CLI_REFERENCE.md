# CLI Reference

## Global Options

```
toolforge [OPTIONS] COMMAND [ARGS]...
```

All commands are run from within a ToolForge workspace (directory containing `.toolforge/`).

---

## `toolforge init [DIRECTORY]`

Initialise a new ToolForge workspace.

```bash
toolforge init                 # current directory
toolforge init ./my-workspace  # specific directory
```

Creates:
```
.toolforge/
tools/
  examples/
  generated/
skills/
  generated/
evals/
  generated/
dist/
toolforge_registry.json
```

---

## `toolforge new tool --from-prompt TEXT`

Scaffold a new tool from a natural-language description.

```bash
toolforge new tool --from-prompt "Create a tool that cleans CSV files"
toolforge new tool --from-prompt "Build a TypeScript tool to fetch GitHub issues"
```

**Steps performed:**
1. `generate_spec_from_prompt(prompt)` → `ToolSpec`
2. `scaffold_tool(spec, tools/generated/)` → files on disk
3. `registry.register(spec)` → entry in `toolforge_registry.json`

**Outputs:** Prints created file paths.

---

## `toolforge generate mcp SLUG`

Generate an MCP server for an existing tool.

```bash
toolforge generate mcp csv-cleaner
```

Reads `tools/generated/csv-cleaner/toolforge.yaml`, generates:
- Python: `server.py`, `pyproject.toml`, `tool.py` (copy), `Dockerfile`
- TypeScript: `index.ts`, `package.json`, `Dockerfile`

---

## `toolforge generate skill SLUG`

Generate a Copilot Skill definition for an existing tool.

```bash
toolforge generate skill csv-cleaner
```

Writes `skills/generated/{category}/{slug}/SKILL.md`.

---

## `toolforge generate eval SLUG`

Generate an evaluation harness for an existing tool.

```bash
toolforge generate eval csv-cleaner
```

Writes `evals/generated/{slug}/task_config.json`, `cases/`, `evaluation.py`.

---

## `toolforge validate SLUG`

Run all validators against a tool.

```bash
toolforge validate csv-cleaner
```

Runs in order:
1. Schema validation (YAML structure)
2. Security policy check
3. MCP server syntax (if MCP enabled)
4. Skill file sections (if skill enabled)
5. pytest test suite

Exits with code 0 if all pass, 1 if any fail.

---

## `toolforge run SLUG --input KEY=VALUE [--timeout SECONDS]`

Run a tool with given inputs.

```bash
toolforge run csv-cleaner --input input_path=examples/input.csv
toolforge run local-file-hasher --input file_path=README.md --input algorithm=sha256
toolforge run my-tool --input '{"key": "value"}'  # JSON object as single arg
```

- `--timeout`: subprocess timeout in seconds (default: 30)
- Inputs are serialised to `TOOLFORGE_INPUTS` env var as JSON
- Exits with the tool's exit code

---

## `toolforge eval SLUG [--timeout SECONDS]`

Run the eval suite for a tool.

```bash
toolforge eval csv-cleaner
toolforge eval csv-cleaner --timeout 60
```

Displays a Rich table with per-case pass/fail/score. Exits 1 if overall pass rate is below baseline.

---

## `toolforge package SLUG [--dist-dir PATH]`

Package a tool into a distributable `.zip` archive.

```bash
toolforge package csv-cleaner
toolforge package csv-cleaner --dist-dir ./releases
```

Creates `dist/{slug}-{version}.zip` containing:
- `manifest.json` — metadata
- All source files (excluding `__pycache__`, `.pyc`, `node_modules`)

---

## `toolforge registry list`

List all registered tools.

```bash
toolforge registry list
```

Displays a Rich table with slug, name, version, language, and tags.

---

## `toolforge registry search TAG`

Search registered tools by tag.

```bash
toolforge registry search csv
toolforge registry search file
```

---

## `toolforge registry info SLUG`

Show detailed information about a registered tool.

```bash
toolforge registry info csv-cleaner
```

---

## `toolforge install SKILL_PATH`

Import a legacy SKILL.md into the workspace.

```bash
toolforge install ./legacy/agent-skills-curated/skills/browser-and-automation/webapp-testing/SKILL.md
toolforge install ./some-skill-directory/
```

Copies to `skills/generated/{category}/{slug}/SKILL.md`.
