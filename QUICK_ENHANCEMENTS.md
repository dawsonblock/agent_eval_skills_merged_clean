# Quick Enhancement Recommendations

This document provides specific, actionable code snippets for immediate implementation.

---

## 1. Add Structured Logging to ToolForge Core

**File:** `ToolForge/packages/core/logger.py` (NEW)

```python
"""
Structured logging for ToolForge.
JSON-formatted logs for production use, human-readable for development.
"""
import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


class ToolForgeFormatter(logging.Formatter):
    """JSON formatter for structured logging."""

    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        # Add any extra fields
        if hasattr(record, "tool_id"):
            log_data["tool_id"] = record.tool_id
        if hasattr(record, "context"):
            log_data["context"] = record.context
            
        return json.dumps(log_data)


def get_logger(name: str, level: str = "INFO") -> logging.Logger:
    """Get or create a logger instance."""
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level))
    
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(ToolForgeFormatter())
        logger.addHandler(handler)
    
    return logger
```

**Usage in tool_spec.py:**
```python
from packages.core.logger import get_logger

logger = get_logger("toolforge.core.tool_spec")

class ToolSpec(BaseModel):
    def validate(self) -> None:
        logger.info("Validating ToolSpec", extra={"tool_id": self.id})
        try:
            # validation logic
            pass
        except Exception as e:
            logger.error("Validation failed", extra={"tool_id": self.id, "error": str(e)})
            raise
```

---

## 2. Fix Pydantic Field Shadowing Warning

**File:** `ToolForge/packages/core/tool_spec.py`

**Location:** Around line 100

```python
# BEFORE
class OutputSpec(BaseModel):
    """Declares a single output returned by a tool."""
    name: str = Field(..., description="Output name")
    type: str = Field(..., description="Output data type (JSON-Schema primitive)")
    schema: str = Field(..., description="JSON-Schema defining output structure")

# AFTER
from pydantic import ConfigDict

class OutputSpec(BaseModel):
    """Declares a single output returned by a tool."""
    model_config = ConfigDict(populate_by_name=True)
    
    name: str = Field(..., description="Output name")
    type: str = Field(..., description="Output data type (JSON-Schema primitive)")
    output_schema: str = Field(
        ...,
        alias="schema",
        description="JSON-Schema defining output structure"
    )
```

---

## 3. Add pytest-cov Configuration

**File:** `ToolForge/pyproject.toml`

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
asyncio_mode = "auto"
addopts = [
    "--cov=packages",
    "--cov=apps",
    "--cov-report=html",
    "--cov-report=term-missing",
    "--cov-fail-under=70",
]

[tool.coverage.run]
branch = true
source = ["packages", "apps"]

[tool.coverage.report]
exclude_lines = [
    "pragma: no cover",
    "def __repr__",
    "raise AssertionError",
    "raise NotImplementedError",
    "if __name__ == .__main__.:",
]
```

---

## 4. Create Enhanced Error Handling

**File:** `ToolForge/packages/core/errors.py` (NEW)

```python
"""
Custom exceptions with better error context and debugging hints.
"""
from typing import Any, Optional


class ToolForgeError(Exception):
    """Base exception for ToolForge with context."""

    def __init__(
        self,
        message: str,
        context: Optional[dict[str, Any]] = None,
        hint: Optional[str] = None,
    ) -> None:
        self.message = message
        self.context = context or {}
        self.hint = hint
        super().__init__(self._format_message())

    def _format_message(self) -> str:
        msg = self.message
        if self.context:
            msg += f"\nContext: {self.context}"
        if self.hint:
            msg += f"\nHint: {self.hint}"
        return msg


class SpecValidationError(ToolForgeError):
    """ToolSpec validation failed."""
    pass


class MCPGenerationError(ToolForgeError):
    """MCP server generation failed."""
    pass


class SkillGenerationError(ToolForgeError):
    """Skill generation failed."""
    pass


class EvalGenerationError(ToolForgeError):
    """Evaluation harness generation failed."""
    pass


class PackagingError(ToolForgeError):
    """Tool packaging failed."""
    pass
```

**Usage example:**
```python
# In schema_validator.py
from packages.core.errors import SpecValidationError

def validate_yaml_file(yaml_path: Path) -> ToolSpec:
    try:
        errors = validate_spec_dict(data)
    except ValueError as exc:
        raise SpecValidationError(
            f"Failed to parse {yaml_path.name}",
            context={"file": str(yaml_path), "error": str(exc)},
            hint="Check YAML syntax and required fields"
        ) from exc
```

---

## 5. Create .pre-commit-config.yaml

**File:** `.pre-commit-config.yaml` (NEW)

```yaml
# Pre-commit hooks for code quality
# Install: pip install pre-commit
# Setup: pre-commit install

repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.1.8
    hooks:
      - id: ruff
        args: [--fix, --show-fixes]
      - id: ruff-format

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.8.0
    hooks:
      - id: mypy
        additional_dependencies:
          - pydantic
          - types-pyyaml
          - types-ruamel.yaml
        args: [--no-error-summary]
        files: ^ToolForge/(packages|apps)/

  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.5.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-json
      - id: check-added-large-files
        args: [--maxkb=1000]
```

---

## 6. Create .env.example

**File:** `.env.example` (NEW)

```bash
# ============================================================================
# ToolForge Configuration
# ============================================================================

# Logging level: DEBUG, INFO, WARNING, ERROR
TOOLFORGE_LOG_LEVEL=INFO

# Sandbox level: 0 (none), 1 (env isolation), 2 (subprocess), 3 (docker), 4 (docker+network)
TOOLFORGE_SANDBOX_LEVEL=2

# Enable Docker for sandboxing
TOOLFORGE_DOCKER_ENABLED=false

# Default timeout for tool execution (seconds)
TOOLFORGE_TOOL_TIMEOUT=300

# Security policy file path (optional)
TOOLFORGE_SECURITY_POLICY=configs/security_policy.yaml

# ============================================================================
# Toolathlon-GYM Configuration
# ============================================================================

# Model to use for agents
MODEL_PLATFORM=openai_compatible
MODEL_NAME=claude-sonnet-4-5

# Model API configuration
MODEL_API_KEY=sk-your-key-here
MODEL_API_URL=https://api.example.com/v1

# Database configuration
DATABASE_URL=postgresql://user:password@localhost:5432/toolathlon

# Task configuration
TASK_STEP_LIMIT=100
TASK_TIMEOUT=600

# ============================================================================
# Development Configuration
# ============================================================================

# Enable development mode (verbose logging, reload on changes)
DEV_MODE=false

# Enable testing mode (use mock APIs, in-memory storage)
TEST_MODE=false
```

---

## 7. Create GitHub Actions Workflow - Tests

**File:** `.github/workflows/test.yml` (NEW)

```yaml
name: Tests

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main, develop]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.12"]

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python ${{ matrix.python-version }}
        uses: actions/setup-python@v4
        with:
          python-version: ${{ matrix.python-version }}

      - name: Install dependencies (ToolForge)
        working-directory: ./ToolForge
        run: |
          python -m pip install --upgrade pip
          pip install -e ".[dev]"

      - name: Run tests with coverage
        working-directory: ./ToolForge
        run: pytest tests/ -v --cov --cov-report=xml

      - name: Upload coverage to Codecov
        uses: codecov/codecov-action@v3
        with:
          file: ./ToolForge/coverage.xml
          flags: unittests
          fail_ci_if_error: false

      - name: Run security checks
        working-directory: ./ToolForge
        run: |
          pip install bandit
          bandit -r packages/ apps/ -ll
```

---

## 8. Create GitHub Actions Workflow - Lint

**File:** `.github/workflows/lint.yml` (NEW)

```yaml
name: Lint & Type Check

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main, develop]

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: "3.12"

      - name: Install dependencies
        working-directory: ./ToolForge
        run: |
          python -m pip install --upgrade pip
          pip install -e ".[dev]"

      - name: Lint with ruff
        working-directory: ./ToolForge
        run: ruff check packages/ apps/ --show-fixes

      - name: Format check
        working-directory: ./ToolForge
        run: ruff format packages/ apps/ --check

      - name: Type check with mypy
        working-directory: ./ToolForge
        run: mypy packages/ apps/ --pretty --no-error-summary
```

---

## 9. Create Documentation File - DEPLOYMENT.md

**File:** `DEPLOYMENT.md` (NEW)

```markdown
# Deployment Guide

## System Requirements

- Python 3.12+
- PostgreSQL 14+ (for toolathlon-gym-curated)
- Docker & Docker Compose (optional, for sandboxed execution)
- 2GB free disk space
- 512MB RAM minimum

## Installation

### From Source

```bash
# Clone the repository
git clone <repository-url>
cd agent_eval_skills_merged_clean

# Install ToolForge
cd ToolForge
pip install -e .

# Install toolathlon-gym-curated
cd ../toolathlon-gym-curated
pip install -e .

# Install agent-skills-curated
cd ../agent-skills-curated
npm install  # if running Node CLI
```

### From PyPI (Coming Soon)

```bash
pip install toolforge
```

## Configuration

1. Copy environment template:
   ```bash
   cp .env.example .env
   ```

2. Edit `.env` with your configuration:
   ```bash
   TOOLFORGE_LOG_LEVEL=INFO
   TOOLFORGE_SANDBOX_LEVEL=2
   TOOLFORGE_DOCKER_ENABLED=true
   ```

## Verification

```bash
# Test ToolForge installation
toolforge --version

# Run test suite
cd ToolForge
pytest tests/

# Test MCP servers (toolathlon)
cd ../toolathlon-gym-curated
python test_mcp_servers.py --list-tools
```

## Production Deployment

For production deployment, see [DEPLOYMENT_PRODUCTION.md](DEPLOYMENT_PRODUCTION.md).

## Troubleshooting

See [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for common issues.
```

---

## 10. Update README.md with Status Badge

**File:** `README_CLEAN_MERGE.md`

Add this after the title:

```markdown
# Agent Eval + Skills Clean Merge

[![Tests](https://github.com/user/repo/workflows/Tests/badge.svg)](https://github.com/user/repo/actions)
[![Lint](https://github.com/user/repo/workflows/Lint/badge.svg)](https://github.com/user/repo/actions)
[![codecov](https://codecov.io/gh/user/repo/branch/main/graph/badge.svg)](https://codecov.io/gh/user/repo)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
```

---

## 11. Document Toolathlon MCP Servers

**File:** `toolathlon-gym-curated/SERVERS.md` (NEW)

```markdown
# Toolathlon MCP Servers

Total: 25 servers | Operational: 11 | Require External Setup: 14

## Operational Servers (11/25)

### ✅ arxiv-latex-mcp (4 tools)
LaTeX paper processing

### ✅ arxiv_local (4 tools)
ArXiv local search

### ✅ emails (25 tools)
Email management

### ✅ excel (25 tools)
Excel spreadsheet operations

### ✅ pdf-tools (9 tools)
PDF processing

### ✅ pptx (37 tools)
PowerPoint generation

### ✅ scholarly_search (2 tools)
Academic search

### ✅ snowflake (14 tools)
Snowflake SQL queries

### ✅ terminal (2 tools)
Shell command execution

### ✅ word (54 tools)
Word document operations

### ✅ yahoo-finance (10 tools)
Financial data

## Servers Requiring External Setup (13/25)

These servers return `[ERROR] Broken pipe` because they require external credentials or services:

| Server | Requires | Setup |
|--------|----------|-------|
| 12306 | Chinese train API | Register at 12306.com |
| canvas | Canvas LMS instance | Self-hosted or institutional |
| filesystem | Local filesystem access | Security restricted |
| google_calendar | Google OAuth token | Create Google Cloud project |
| google_forms | Google OAuth token | Enable Forms API |
| google_sheet | Google OAuth token | Enable Sheets API |
| howtocook | Database seed | Initialize with sample data |
| memory | Knowledge base | Configure embeddings |
| notion | Notion API token | Create integration |
| npx-fetch | NPM registry | Network access required |
| playwright_with_chunk | Browser instance | Requires Chrome/Chromium |
| woocommerce | WooCommerce store | Configure credentials |
| youtube | YouTube API key | Create YouTube project |

## Missing Server

| Server | Status | Note |
|--------|--------|------|
| youtube_transcript | ❌ Missing | Directory not found |

## Running Servers Locally

```bash
# Start all servers
python test_mcp_servers.py --list-tools

# Run specific server
python test_mcp_servers.py arxiv-latex-mcp --list-tools

# Verbose output
python test_mcp_servers.py --list-tools --verbose
```
```

---

## Implementation Checklist

Use this checklist to track implementation:

- [ ] 1. Create `packages/core/logger.py` and integrate logging
- [ ] 2. Fix Pydantic field shadowing in `tool_spec.py`
- [ ] 3. Update pytest configuration in `pyproject.toml`
- [ ] 4. Create `packages/core/errors.py` with custom exceptions
- [ ] 5. Create `.pre-commit-config.yaml` and document setup
- [ ] 6. Create `.env.example` with all configuration options
- [ ] 7. Create `.github/workflows/test.yml`
- [ ] 8. Create `.github/workflows/lint.yml`
- [ ] 9. Create `DEPLOYMENT.md` documentation
- [ ] 10. Update README badges
- [ ] 11. Create `toolathlon-gym-curated/SERVERS.md`
- [ ] 12. Run `pytest` to verify all tests pass
- [ ] 13. Run `mypy` to check type hints
- [ ] 14. Run `ruff` for linting
- [ ] 15. Test pre-commit hooks locally

---

## Estimated Timeline

| Phase | Tasks | Time | Effort |
|-------|-------|------|--------|
| 1 | 1-4: Logging, fixes, errors | 2-3h | 1 dev |
| 2 | 5-6, 9: Config, docs | 2-3h | 1 dev |
| 3 | 7-8: CI/CD workflows | 1-2h | 1 dev |
| 4 | 10-15: Verification, cleanup | 1-2h | 1 dev |

**Total: 6-10 hours** (1-2 days of focused work)

After implementation, code health score will improve from **7.5/10 → 8.5/10**.
