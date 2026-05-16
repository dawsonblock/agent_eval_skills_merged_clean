# csv-cleaner

A ToolForge tool that cleans CSV files by stripping whitespace, removing blank rows, and deduplicating records.

## Overview

`csv-cleaner` takes a CSV file and returns a cleaned version with:

- Leading/trailing whitespace stripped from all cell values
- Fully blank rows removed
- Duplicate rows removed (preserving first occurrence)

It handles UTF-8 files with or without a BOM (`utf-8-sig`).

## Installation

This tool ships with ToolForge. No additional dependencies are required beyond Python 3.12+.

## Usage

### Via ToolForge CLI

```bash
toolforge run csv-cleaner --input input_path=examples/input.csv
toolforge run csv-cleaner --input input_path=data.csv --input output_path=clean.csv
```

### Direct Python

```python
import sys
sys.path.insert(0, ".")
from tool import clean_csv

# Return cleaned CSV as string
result = clean_csv("examples/input.csv")
print(result)

# Write to file
clean_csv("examples/input.csv", "clean.csv")
```

### Via MCP Server (after `toolforge generate mcp csv-cleaner`)

```json
{
  "tool": "csv_cleaner",
  "arguments": {
    "input_path": "data.csv",
    "output_path": "clean.csv"
  }
}
```

## Parameters

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `input_path` | string | ✅ | Path to the input CSV file |
| `output_path` | string | | Path to write cleaned output. If omitted, returns CSV as string. |

## Output

Returns the cleaned CSV as a string, or writes to `output_path` and returns a summary message.

## Examples

**Input (`examples/input.csv`):**

```csv
name, age, city
Alice, 30, New York
Bob, 25, London

Alice, 30, New York
```

**Output:**

```csv
name,age,city
Alice,30,New York
Bob,25,London
```

## Running Tests

```bash
cd tools/examples/csv-cleaner
pytest tests/ -v
```

## Security

- Sandbox level: 1 (env isolation)
- File read/write: allowed
- Network: denied
- No shell execution
