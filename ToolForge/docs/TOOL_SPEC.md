# toolforge.yaml Reference

Every tool managed by ToolForge is described by a `toolforge.yaml` file in its root directory. This document is the authoritative field reference.

---

## Minimal Example

```yaml
name: My Tool
slug: my-tool
version: "0.1.0"
description: "A short description of what the tool does."
language: python
entry_point: tool.py
```

---

## Top-Level Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | ✅ | Human-readable name |
| `slug` | string | ✅ | URL-safe identifier (kebab-case) |
| `version` | string | ✅ | Semver string e.g. `"0.1.0"` |
| `description` | string | ✅ | Short description (≤ 200 chars recommended) |
| `language` | `python` \| `typescript` | ✅ | Implementation language |
| `entry_point` | string | ✅ | Relative path to main file e.g. `tool.py` |
| `author` | string | | Tool author name |
| `tags` | list[string] | | Searchable tags |
| `capabilities` | list[string] | | From: `file_read`, `file_write`, `network`, `shell`, `database`, `llm` |
| `dependencies` | list[string] | | Package dependencies (pip/npm format) |
| `source_prompt` | string | | The original prompt used to generate the spec |
| `source_prompt_raw` | string | | Unmodified source prompt for provenance/audit |

---

## `parameters`

List of `ParameterSpec` objects describing tool inputs.

```yaml
parameters:
  - name: input_path
    type: string
    description: "Path to input CSV file"
    required: true
  - name: output_path
    type: string
    description: "Path for cleaned output (optional)"
    required: false
    default: ""
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | ✅ | Parameter name |
| `type` | string | ✅ | JSON Schema type: `string`, `integer`, `number`, `boolean`, `array`, `object` |
| `description` | string | ✅ | What this parameter does |
| `required` | boolean | | Defaults to `true` |
| `default` | string | | Default value (as string) |
| `enum` | list | | Allowed values |

---

## `output`

```yaml
output:
  type: string
  description: "Cleaned CSV content or path to output file"
```

---

## `security`

```yaml
security:
  sandbox_level: 1        # 0–4 (see ARCHITECTURE.md)
  allow_network: false
  allow_file_read: true
  allow_file_write: true
  privacy_level: internal  # public | internal | confidential | restricted
  denied_imports:
    - subprocess
    - socket
```

---

## `eval`

```yaml
eval:
  enabled: true
  baseline_pass_rate: 0.8   # fraction 0–1
  criteria:
    - name: no_error
      type: no_error
      weight: 1.0
    - name: output_matches
      type: exact_match
      weight: 1.0
      threshold: 1.0
  cases:
    - id: smoke-01
      inputs:
        input_path: examples/input.csv
      description: "Smoke test with sample input"
      tags:
        - smoke
    - id: dedup-01
      inputs:
        input_path: examples/duplicates.csv
      expected_output: "name,age\nAlice,30\nBob,25\n"
      description: "Deduplication test"
      tags:
        - correctness
```

### `EvalCriterionType` Values

| Value | Meaning |
|-------|---------|
| `exact_match` | Output equals `expected_output` exactly |
| `contains` | Output contains `expected_output` as substring |
| `no_error` | Exit code 0, no stderr |
| `performance` | Wall time below `threshold` seconds |
| `semantic` | Semantic similarity ≥ `threshold` |
| `rubric` | Rubric-based judge scoring |

---

## `mcp`

```yaml
mcp:
  enabled: true
  language: python     # python | typescript (defaults to tool language)
  transport: stdio     # stdio | http
```

---

## `skill`

```yaml
skill:
  enabled: true
  category: file-processing   # used as directory name under skills/
```

---

## Complete Example

```yaml
name: CSV Cleaner
slug: csv-cleaner
version: "0.1.0"
description: "Cleans CSV files by stripping whitespace, removing blank rows, and deduplicating."
language: python
entry_point: tool.py
author: "ToolForge"
tags:
  - csv
  - file-processing
  - data-cleaning
capabilities:
  - file_read
  - file_write
dependencies:
  - "python>=3.12"

parameters:
  - name: input_path
    type: string
    description: "Path to the input CSV file"
    required: true
  - name: output_path
    type: string
    description: "Path to write the cleaned CSV (optional, returns string if omitted)"
    required: false
    default: ""

output:
  type: string
  description: "Cleaned CSV content or path to the output file"

security:
  sandbox_level: 1
  allow_network: false
  allow_file_read: true
  allow_file_write: true
  privacy_level: internal

mcp:
  enabled: true
  transport: stdio

skill:
  enabled: true
  category: file-processing

eval:
  enabled: true
  baseline_pass_rate: 0.8
  criteria:
    - name: no_error
      type: no_error
      weight: 1.0
  cases:
    - id: smoke-01
      inputs:
        input_path: examples/input.csv
      description: "Basic smoke test"
      tags:
        - smoke
```
