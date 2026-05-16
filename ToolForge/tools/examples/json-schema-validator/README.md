# json-schema-validator

A ToolForge tool that validates JSON data against a JSON Schema (Draft 7).

## Overview

`json-schema-validator` takes a JSON payload and a JSON Schema and returns a validation report:

```json
{
  "valid": true,
  "errors": []
}
```

or

```json
{
  "valid": false,
  "errors": ["'name' is a required property", "'age' is not of type 'integer'"]
}
```

Both the data and schema can be provided as inline JSON strings **or** as file paths.

## Requirements

```
jsonschema>=4.0
```

Install via pip:

```bash
pip install jsonschema
```

## Usage

### Via ToolForge CLI

```bash
toolforge run json-schema-validator \
  --input data_raw='{"name": "Alice", "age": 30}' \
  --input schema_raw='{"type": "object", "required": ["name"]}'
```

### File paths

```bash
toolforge run json-schema-validator \
  --input data_raw=my_data.json \
  --input schema_raw=my_schema.json
```

### Direct Python

```python
from tool import validate_json

result = validate_json(
    data_raw='{"name": "Alice", "age": 30}',
    schema_raw='{"type": "object", "required": ["name"], "properties": {"name": {"type": "string"}, "age": {"type": "integer"}}}',
)
print(result)
# {'valid': True, 'errors': []}
```

## Parameters

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `data_raw` | string | ✅ | JSON string to validate, or file path to JSON file |
| `schema_raw` | string | ✅ | JSON Schema string, or file path to schema file |

## Output

JSON object:

| Field | Type | Description |
|-------|------|-------------|
| `valid` | boolean | `true` if the data is valid against the schema |
| `errors` | array of strings | Validation error messages (empty when valid) |

## Running Tests

```bash
cd tools/examples/json-schema-validator
pip install jsonschema pytest
pytest tests/ -v
```

## Security

- Sandbox level: 0 (direct)
- File read: allowed
- Network: denied
- No shell execution
