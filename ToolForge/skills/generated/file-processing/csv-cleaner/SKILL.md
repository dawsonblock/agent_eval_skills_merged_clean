---
name: csv-cleaner
description: >
  Clean CSV files by trimming whitespace and normalizing column names.
  WHEN: .
  
---

# Skill: CSV Cleaner

## Purpose

Clean CSV files by trimming whitespace, normalizing column names, removing blank rows, and exporting JSON output.

## Use When


- You need local CSV cleaning for file-based workflows.


## Do Not Use When


- The input is Excel, PDF, a database table, or a URL.
- You need unrestricted file system access.


## Inputs


- input_path (string): Path to CSV file to clean (e.g., examples/input.csv)

- output_path (string, optional), default=outputs/cleaned.csv: Path where cleaned CSV will be written (e.g., outputs/cleaned.csv)


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

Clean valid CSV file

```json
{
  "input_path": "examples/input.csv"
}
```

### case-02-invalid-input

Reject missing input file

```json
{
  "input_path": "examples/missing.csv"
}
```

### case-03-safety-boundary

Path traversal attempt (should be blocked)

```json
{
  "input_path": "../../../etc/passwd"
}
```

### case-04-empty-file

Empty CSV file

```json
{
  "input_path": "examples/empty.csv",
  "output_path": "outputs/empty_cleaned.csv"
}
```

