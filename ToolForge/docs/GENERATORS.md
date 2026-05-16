# Generators Reference

ToolForge generators read a `ToolSpec` and produce ready-to-use files from Jinja2 templates.

---

## `tool_generator.scaffold_tool(spec, output_root, overwrite=False)`

Scaffolds a complete tool directory.

```python
from packages.core.tool_generator import scaffold_tool
from packages.core.tool_spec import ToolSpec

spec = ToolSpec.from_yaml("toolforge.yaml")
created = scaffold_tool(spec, output_root=Path("tools/generated"))
```

**Output structure:**

```
tools/generated/{slug}/
├── toolforge.yaml
├── tool.py
├── README.md
└── tests/
    └── test_{slug}.py
```

- Raises `FileExistsError` if `{slug}/` already exists and `overwrite=False`
- Returns `list[Path]` of created files

---

## `mcp_generator.generate_mcp_server(spec, output_root, overwrite=False)`

Generates an MCP server for the tool. Language is determined by `spec.mcp.language` (defaults to `spec.language`).

```python
from packages.core.mcp_generator import generate_mcp_server

created = generate_mcp_server(spec, output_root=Path("tools/generated"))
```

**Python output:**

```
tools/generated/{slug}/mcp/
├── server.py       # MCP server using mcp>=1.10.1
├── tool.py         # copy of tool source
├── pyproject.toml
└── Dockerfile
```

**TypeScript output:**

```
tools/generated/{slug}/mcp/
├── index.ts        # MCP server using @modelcontextprotocol/sdk ^1.6.1
├── package.json
└── Dockerfile
```

### MCP Protocol Details

- Transport: `stdio` (default) or `http`
- Python server uses `mcp.Server`, `mcp.stdio_server`, `mcp.Tool`, `mcp.TextContent`
- TypeScript server uses `@modelcontextprotocol/sdk` `Server` + `StdioServerTransport`
- Tool inputs are forwarded via `TOOLFORGE_INPUTS` env var

---

## `skill_generator.generate_skill(spec, output_root, overwrite=False)`

Generates a Copilot Skill SKILL.md file.

```python
from packages.core.skill_generator import generate_skill

created = generate_skill(spec, output_root=Path("skills/generated"))
```

**Output:**

```
skills/generated/{category}/{slug}/
└── SKILL.md
```

The `category` comes from `spec.skill.category`. SKILL.md is rendered from `skill_template/SKILL.md.j2` and contains all required sections.

**Required sections in generated SKILL.md:**
`Overview`, `Usage`, `Parameters`, `Output`, `Examples`, `When to Use`, `Security`, `Tags`

---

## `eval_generator.generate_eval(spec, output_root, overwrite=False)`

Generates an evaluation harness.

```python
from packages.core.eval_generator import generate_eval

created = generate_eval(spec, output_root=Path("evals/generated"))
```

**Output:**

```
evals/generated/{slug}/
├── task_config.json         # eval metadata + criteria
├── evaluation.py            # scorer/judge logic
└── cases/
    ├── case-01.json
    └── ...
```

---

## `doc_generator.generate_docs(spec, output_root, overwrite=False)`

Generates a standalone README.md.

```python
from packages.core.doc_generator import generate_docs

created = generate_docs(spec, output_root=Path("."))
```

---

## Templates

All templates live under `packages/templates/` and use Jinja2 with:
- `StrictUndefined` — raises on undefined variables
- Custom `tojson` filter: `json.dumps(value, indent=indent)`
- No HTML autoescaping

| Template | Used By |
|----------|---------|
| `mcp_server_python/server.py.j2` | `mcp_generator` (Python) |
| `mcp_server_python/tool.py.j2` | `mcp_generator` (Python) |
| `mcp_server_python/pyproject.toml.j2` | `mcp_generator` (Python) |
| `mcp_server_typescript/index.ts.j2` | `mcp_generator` (TypeScript) |
| `mcp_server_typescript/package.json.j2` | `mcp_generator` (TypeScript) |
| `skill_template/SKILL.md.j2` | `skill_generator` |
| `eval_task_template/task_config.json.j2` | `eval_generator` |
| `eval_task_template/agent_system_prompt.md.j2` | `eval_generator` |
| `eval_task_template/evaluation.py.j2` | `eval_generator` |
| `readme_template/README.md.j2` | `doc_generator`, `tool_generator` |
| `docker_template/Dockerfile.j2` | `mcp_generator` |
