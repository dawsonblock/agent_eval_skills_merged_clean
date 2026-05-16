# Integrations Reference

ToolForge integrates with two external ecosystems:

1. **Agent Skills** — import Copilot Skill definitions from existing skill repositories
2. **Toolathlon Gym** — bridge tasks and MCP server configs from the toolathlon evaluation framework

---

## Agent Skills Importer

`packages/integrations/agent_skills/importer.py`

### `import_skill(skill_path, skills_root) → list[Path]`

Imports a SKILL.md file (or a directory containing one) into the ToolForge workspace.

```python
from packages.integrations.agent_skills.importer import import_skill
from pathlib import Path

created = import_skill(
    skill_path=Path("legacy/agent-skills-curated/skills/browser-and-automation/webapp-testing/SKILL.md"),
    skills_root=Path("skills/generated"),
)
# → [skills/generated/browser-and-automation/webapp-testing/SKILL.md]
```

**Behaviour:**
- Accepts either a `SKILL.md` file path or a directory containing one
- Infers `slug` from `skill_dir.name`
- Infers `category` from `skill_dir.parent.name` (falls back to `"general"`)
- Copies SKILL.md to `skills_root/{category}/{slug}/SKILL.md`
- Copies any other non-SKILL.md, non-directory files alongside

**CLI equivalent:**

```bash
toolforge install ./legacy/agent-skills-curated/skills/pdf-and-documents/pdf/SKILL.md
```

---

## Toolathlon Integration

`packages/integrations/toolathlon/`

### Task Adapter

`packages/integrations/toolathlon/task_adapter.py`

#### `load_toolathlon_task(task_path) → dict`

Loads a toolathlon task file (JSON or YAML by extension).

#### `task_to_eval_cases(task) → list[EvalCase]`

Converts a parsed toolathlon task dict to `EvalCase` objects.

```python
from packages.integrations.toolathlon.task_adapter import load_toolathlon_task, task_to_eval_cases

task = load_toolathlon_task(Path("legacy/toolathlon-gym-curated/tasks/finalpool/arxiv-search.json"))
cases = task_to_eval_cases(task)
```

Field mapping:

| Toolathlon field | EvalCase field |
|-----------------|----------------|
| `task_id` / `id` | `id` |
| `description` | `description` |
| `inputs` | `inputs` |
| `expected_output` / `answer` | `expected_output` |
| `tags` | `tags` |

#### `load_eval_cases_from_dir(tasks_dir) → list[EvalCase]`

Recursively loads all `.json` task files from a directory.

```python
from packages.integrations.toolathlon.task_adapter import load_eval_cases_from_dir

cases = load_eval_cases_from_dir(Path("legacy/toolathlon-gym-curated/tasks/finalpool"))
```

---

### Config Bridge

`packages/integrations/toolathlon/config_bridge.py`

#### `load_toolathlon_config(config_path) → dict`

Loads a toolathlon MCP server YAML config.

#### `toolathlon_config_to_mcp_spec(config) → MCPSpec`

Converts a toolathlon server config to an `MCPSpec`.

#### `toolathlon_config_to_partial_spec(config, slug=None) → ToolSpec`

Builds a minimal `ToolSpec` from a toolathlon server config. Detects language from the `command` field (`python` vs other).

```python
from packages.integrations.toolathlon.config_bridge import (
    load_toolathlon_config,
    toolathlon_config_to_partial_spec,
)

config = load_toolathlon_config(Path("legacy/toolathlon-gym-curated/configs/mcp_servers/arxiv-latex-mcp.yaml"))
spec = toolathlon_config_to_partial_spec(config, slug="arxiv-latex-mcp")
```

---

### Runner Bridge

`packages/integrations/toolathlon/runner_bridge.py`

#### `run_toolathlon_tasks(spec, tool_dir, tasks_dir, timeout_s=30.0) → EvalReport`

Loads toolathlon task cases from `tasks_dir` and runs them through the ToolForge eval runner.

```python
from packages.integrations.toolathlon.runner_bridge import run_toolathlon_tasks

report = run_toolathlon_tasks(
    spec=spec,
    tool_dir=Path("tools/generated/arxiv-latex-mcp"),
    tasks_dir=Path("legacy/toolathlon-gym-curated/tasks/finalpool"),
    timeout_s=60.0,
)

print(f"Pass rate: {report.pass_rate:.0%}")
for result in report.results:
    status = "✓" if result.passed else "✗"
    print(f"  {status} {result.case_id}: score={result.score:.2f}")
```

**How it works:**
1. Calls `load_eval_cases_from_dir(tasks_dir)` to collect cases
2. Creates an ephemeral `EvalSpec` with loaded cases, preserving original criteria and baseline
3. Patches the spec via `spec.model_copy(update={"eval": eval_spec})`
4. Delegates to `run_evals(patched_spec, tool_dir, timeout_s=timeout_s)`

---

## Working with Legacy Repos

Both legacy repos are available under `ToolForge/legacy/`:

```
legacy/
├── agent-skills-curated/
│   └── skills/
│       ├── browser-and-automation/webapp-testing/SKILL.md
│       ├── coding-agents-and-ides/mcp-builder/SKILL.md
│       └── ...
└── toolathlon-gym-curated/
    ├── configs/mcp_servers/    # toolathlon YAML configs
    └── tasks/finalpool/        # toolathlon task JSON files
```

### Bulk import all legacy skills

```python
from pathlib import Path
from packages.integrations.agent_skills.importer import import_skill

skills_root = Path("skills/generated")
legacy_skills = Path("legacy/agent-skills-curated/skills")

for skill_md in legacy_skills.rglob("SKILL.md"):
    import_skill(skill_md, skills_root)
```
