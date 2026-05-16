# local-file-hasher

A ToolForge tool that computes cryptographic hashes of local files.

## Overview

`local-file-hasher` reads a file from disk and returns its hash digest along with file metadata. Supports MD5, SHA-256, and SHA-512.

Example output:

```json
{
  "file": "/path/to/sample.txt",
  "algorithm": "sha256",
  "hash": "a3f5b2...",
  "size_bytes": 19
}
```

## Usage

### Via ToolForge CLI

```bash
# Default algorithm (sha256)
toolforge run local-file-hasher --input file_path=README.md

# Specify algorithm
toolforge run local-file-hasher --input file_path=README.md --input algorithm=md5
```

### Direct Python

```python
from tool import hash_file

result = hash_file("examples/sample.txt", algorithm="sha256")
print(result)
# {'file': 'examples/sample.txt', 'algorithm': 'sha256', 'hash': '...', 'size_bytes': 19}
```

### Via MCP Server (after `toolforge generate mcp local-file-hasher`)

```json
{
  "tool": "local_file_hasher",
  "arguments": {
    "file_path": "README.md",
    "algorithm": "sha256"
  }
}
```

## Parameters

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `file_path` | string | ✅ | Path to the file to hash |
| `algorithm` | string | | Hash algorithm: `md5`, `sha256` (default), `sha512` |

## Output

JSON object:

| Field | Type | Description |
|-------|------|-------------|
| `file` | string | Absolute path to the hashed file |
| `algorithm` | string | Algorithm used |
| `hash` | string | Hex digest |
| `size_bytes` | integer | File size in bytes |

## Supported Algorithms

| Algorithm | Digest length | Notes |
|-----------|--------------|-------|
| `md5` | 32 hex chars | Fast; not cryptographically secure |
| `sha256` | 64 hex chars | Recommended default |
| `sha512` | 128 hex chars | Highest security |

## Running Tests

```bash
cd tools/examples/local-file-hasher
pytest tests/ -v
```

## Security

- Sandbox level: 2 (timeout + env isolation)
- File read: allowed
- File write: denied
- Network: denied
- Files are read in 64 KB chunks — safe for large files
