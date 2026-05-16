# Validators Reference

`toolforge validate <slug>` runs five validators in sequence. All validators raise typed exceptions or return lists of error strings — the CLI aggregates them and exits with code 1 on any failure.

---

## 1. `schema_validator.validate_yaml_file(yaml_path)`

Validates a `toolforge.yaml` file against the ToolForge JSON Schema and Pydantic v2 model.

```python
from packages.validators.schema_validator import validate_yaml_file, SchemaValidationError
from pathlib import Path

try:
    spec = validate_yaml_file(Path("tools/generated/csv-cleaner/toolforge.yaml"))
except SchemaValidationError as e:
    print(e.errors)   # list[str]
except FileNotFoundError:
    print("File not found")
```

**Raises:**
- `SchemaValidationError(errors: list[str])` — structural or Pydantic validation failures
- `FileNotFoundError` — if the yaml file does not exist

**Returns:** `ToolSpec` on success.

---

## 2. `security_validator.validate_security(spec, policy_path=None)`

Checks the spec's security configuration against the workspace security policy (`configs/security_policy.yaml`).

```python
from packages.validators.security_validator import validate_security, SecurityViolation

violations = validate_security(spec)
if violations:
    print(violations)   # list[str]

# Raises SecurityViolation if using enforce_security()
from packages.validators.security_validator import enforce_security
enforce_security(spec)  # raises SecurityViolation(violations=[...]) on failure
```

**`validate_security` returns:** `list[str]` (empty = compliant)
**`enforce_security` raises:** `SecurityViolation(violations: list[str])`

**Checks performed:**
- Sandbox level vs. policy minimum
- Network access allowed/denied
- File read/write permissions
- Privacy level compliance

---

## 3. `mcp_validator.validate_mcp_server(spec, mcp_dir)`

Validates a generated MCP server directory.

```python
from packages.validators.mcp_validator import validate_mcp_server, MCPValidationError

errors = validate_mcp_server(spec, mcp_dir=Path("tools/generated/csv-cleaner/mcp"))
```

**Python checks:**
- `server.py` exists
- `server.py` syntax via `py_compile.compile(doraise=True)`
- `pyproject.toml` exists

**TypeScript checks:**
- `index.ts` exists
- `package.json` exists

**Returns:** `list[str]` errors (empty = valid).
**`MCPValidationError(errors: list[str])`** is raised by the CLI when errors are found.

---

## 4. `skill_validator.validate_skill_file(skill_path)`

Validates a SKILL.md file for required structure.

```python
from packages.validators.skill_validator import validate_skill_file

errors = validate_skill_file(Path("skills/generated/general/csv-cleaner/SKILL.md"))
```

**Required sections** (must appear as `## Section` headings):

| Section |
|---------|
| Overview |
| Usage |
| Parameters |
| Output |
| Examples |
| When to Use |
| Security |
| Tags |

**Required frontmatter keys:**

| Key |
|-----|
| `name` |
| `description` |

**Returns:** `list[str]` errors (empty = valid).

---

## 5. `test_validator.run_tests(tool_dir, timeout=60)`

Runs the tool's pytest test suite and returns a structured report.

```python
from packages.validators.test_validator import run_tests, TestReport

report: TestReport = run_tests(Path("tools/generated/csv-cleaner"), timeout=60)
print(f"Passed: {report.passed}, Failed: {report.failed}, Errors: {report.errors}")
```

**`TestReport` fields:**

| Field | Type | Description |
|-------|------|-------------|
| `passed` | int | Number of passing tests |
| `failed` | int | Number of failing tests |
| `errors` | int | Number of test errors (collection failures) |
| `skipped` | int | Number of skipped tests |
| `duration` | float | Total duration in seconds |
| `failures` | list[dict] | Per-failure details from `--json-report` |

Internally runs: `pytest tests/ --json-report --json-report-file=...` with the given timeout.

---

## Safety Analyzer (`packages/core/safety_analyzer`)

Not a validator but called by the CLI's validate flow. Scans tool source files statically.

```python
from packages.core.safety_analyzer import analyze_safety, SafetyReport

report: SafetyReport = analyze_safety(spec, tool_dir=Path("tools/generated/csv-cleaner"))
if report.issue_count > 0:
    for issue in report.issues:
        print(f"[{issue.severity}] {issue.message} — {issue.file}:{issue.line}")
```

**Detected patterns:**

| Pattern | Check |
|---------|-------|
| Hardcoded secrets | `*_KEY`, `*_SECRET`, `*_TOKEN`, `*_PASSWORD`, etc. |
| Path traversal | `../` in string literals |
| Shell execution | `os.system`, `subprocess.call/run/Popen` |
| Denied imports | Configurable list (default: `subprocess`, `socket`) |
