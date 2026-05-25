---
name: create-a-tool-named
description: >
  Create a tool named 'pdf-to-markdown' that Build me a local skill that converts PDF text to Markdown without OCR or netw.
  WHEN: .
  
---

# Skill: Create A Tool Named

## Purpose

Create a tool named 'pdf-to-markdown' that Build me a local skill that converts PDF text to Markdown without OCR or network access

## Use When


- You need local CSV cleaning for file-based workflows.


## Do Not Use When


- The input is Excel, PDF, a database table, or a URL.
- You need unrestricted file system access.


## Inputs


- input (string): Primary input for the tool


## Outputs

- Tool output

## Safety Rules

- File access is restricted by ToolForge path policy.
- Path traversal and blocked paths must be rejected before execution.
- Non-CSV inputs must be rejected for CSV-only tools.

## Procedure

1. Validate input parameters.
2. Verify path constraints and extension rules.
3. Run the tool and capture structured output.
4. Confirm expected output files are present.

## Validation Checklist

- `cleaned_path` exists in output payload for success cases.
- Row and header counts are consistent.
- Output file exists when expected.
- Unsafe path inputs fail safely.

## Failure Modes

- Missing input file.
- Invalid extension.
- Path policy violation.
- Unexpected runtime exception.

## Examples


### case-01-success

Basic tool invocation

```json
{
  "input": "test_data"
}
```

