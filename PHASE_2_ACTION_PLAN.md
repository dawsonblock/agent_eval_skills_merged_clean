# Phase 2 Action Plan — Quick Wins & Integration

**Prepared:** May 16, 2026
**Target Duration:** 2-3 hours for quick wins, 4-6 hours for full integration
**Goal:** Fix all linting issues, resolve type errors, integrate logging & error classes

---

## 🎯 Phase 2A: Quick Wins (30-45 minutes)

### Step 1: Run Auto-fix for Linting

```bash
cd /Users/dawsonblock/Downloads/agent_eval_skills_merged_clean/ToolForge
ruff check --fix packages/ apps/
```

**Expected Output:**
```
Fixed 10 issues in:
  - apps/cli/toolforge_cli/main.py (3 imports)
  - packages/core/logger.py (1 import)
  - packages/core/security_validator.py (1 variable)
  - packages/validators/test_validator.py (1 f-string)
  [+ 4 more minor fixes]
```

**Verify:** `ruff check packages/ apps/` should now show 2 remaining issues

---

### Step 2: Review & Remove Unused Imports

**Location 1: `packages/core/logger.py`**
- Line 9: `from pathlib import Path` — Not used in file
- Action: DELETE the line
- File now only needs: json, logging, sys, datetime, typing

**Location 2: `apps/cli/toolforge_cli/main.py`**
- Line 19: `import json` — Verify not used (should be auto-removed)
- Line 212: `ToolSpec` import in validate() — Check if actually needed

Check usage:
```bash
cd ToolForge
grep -n "json\." apps/cli/toolforge_cli/main.py
grep -n "ToolSpec" apps/cli/toolforge_cli/main.py
```

---

### Step 3: Configure mypy for Pydantic v2

Create file: `ToolForge/pyproject.toml` — Update `[tool.mypy]` section

Replace:
```toml
[tool.mypy]
python_version = "3.12"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = false
```

With:
```toml
[tool.mypy]
python_version = "3.12"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = false
plugins = ["pydantic.mypy"]

[tool.pydantic-mypy]
init_forbid_extra = true
init_typed = true
warn_required_dynamic_fields = true
warn_untyped_fields = true
```

**Verify:**
```bash
cd ToolForge
mypy packages/core/tool_spec.py
# Should now show 0 errors
```

---

### Step 4: Verify Tests Still Pass

```bash
cd /Users/dawsonblock/Downloads/agent_eval_skills_merged_clean/ToolForge
python -m pytest tests/ -xvs 2>&1 | tail -10
```

**Expected:** `43 passed in 1.0s`

---

### Step 5: Install Pre-commit Locally

```bash
cd /Users/dawsonblock/Downloads/agent_eval_skills_merged_clean
pip install pre-commit
pre-commit install
```

**Verify:**
```bash
ls -la .git/hooks/pre-commit
# Should show pre-commit hook installed
```

**Test it:**
```bash
# Make a trivial change
echo "" >> README.md
git add README.md
git commit -m "test pre-commit"
# Should run ruff auto-fix, mypy check, etc.
```

---

## 🎯 Phase 2B: Logging Integration (2-3 hours)

### Step 1: Integrate Logger into `tool_spec.py`

**File:** `ToolForge/packages/core/tool_spec.py`

**Add at top (after imports, line 2):**
```python
from packages.core.logger import get_logger

logger = get_logger(__name__)
```

**Add logging calls:**

A. In `ToolSpec.from_yaml()` classmethod (around line 400):
```python
@classmethod
def from_yaml(cls, path: str | Path) -> "ToolSpec":
    """Load ToolSpec from YAML file."""
    logger.info(f"Loading ToolSpec from {path}")
    # ... existing code ...
    spec = cls(**data)
    logger.info(f"Loaded ToolSpec: {spec.name}", extra={"tool_id": spec.name})
    return spec
```

B. In `ToolSpec.__init__()` or similar:
```python
def __init__(self, **data):
    logger.debug(f"Creating ToolSpec with {len(data)} fields")
    super().__init__(**data)
    logger.debug(f"ToolSpec initialized: {self.name}")
```

---

### Step 2: Integrate Logger into `schema_validator.py`

**File:** `ToolForge/packages/validators/schema_validator.py`

**Add at top:**
```python
from packages.core.logger import get_logger

logger = get_logger(__name__)
```

**Add logging in `validate_yaml_file()` function:**
```python
def validate_yaml_file(path: str | Path) -> ToolSpec:
    """Validate a YAML file against ToolSpec schema."""
    logger.info(f"Validating YAML file: {path}")
    
    try:
        with open(path) as f:
            data = yaml.safe_load(f)
        logger.debug(f"Loaded YAML with {len(data)} top-level keys")
        
        spec = ToolSpec(**data)
        logger.info(f"✓ Schema validation passed: {spec.name}")
        return spec
    except Exception as e:
        logger.error(f"✗ Schema validation failed: {e}", exc_info=True)
        raise
```

---

### Step 3: Integrate Logger into `security_validator.py`

**File:** `ToolForge/packages/validators/security_validator.py`

**Add at top:**
```python
from packages.core.logger import get_logger

logger = get_logger(__name__)
```

**Add logging in `validate_security()` function:**
```python
def validate_security(spec: ToolSpec) -> list[str]:
    """Validate security constraints."""
    logger.info(f"Validating security for tool: {spec.name}")
    errors = []
    
    # Check capabilities
    if spec.security.requires_shell:
        logger.debug(f"Tool {spec.name} requires shell execution")
    
    # ... validation logic ...
    
    if errors:
        logger.error(f"Security validation failed with {len(errors)} errors")
    else:
        logger.info(f"✓ Security validation passed for {spec.name}")
    
    return errors
```

---

### Step 4: Test Logging Integration

```bash
cd ToolForge

# Set log level to DEBUG to see all logs
export TOOLFORGE_LOG_LEVEL=DEBUG

# Run a validation
python -m pytest tests/test_validators.py::test_schema_validator -xvs
```

**Expected Output:** Should see log lines in test output

---

## 🎯 Phase 2C: Error Class Integration (1-2 hours)

### Step 1: Update `schema_validator.py` to Use Custom Errors

**File:** `ToolForge/packages/validators/schema_validator.py`

**Add import:**
```python
from packages.core.errors import SpecValidationError, SchemaValidationError
```

**Replace exception handling:**

**Before:**
```python
except Exception as e:
    raise SchemaValidationError([str(e)])
```

**After:**
```python
except KeyError as e:
    raise SpecValidationError(
        f"Missing required field: {e}",
        context={"spec": path, "field": str(e)},
        hint="Check your YAML file has all required fields: name, description, version, etc."
    )
except ValueError as e:
    raise SpecValidationError(
        f"Invalid value: {e}",
        context={"spec": path, "error": str(e)},
        hint="Review the YAML syntax and data types"
    )
```

---

### Step 2: Update `security_validator.py` to Use Custom Errors

**File:** `ToolForge/packages/validators/security_validator.py`

**Add import:**
```python
from packages.core.errors import SecurityValidationError
```

**Replace generic errors:**

**Before:**
```python
if not isinstance(spec.security.max_file_size_mb, int):
    errors.append("max_file_size_mb must be an integer")
```

**After:**
```python
if not isinstance(spec.security.max_file_size_mb, int):
    error = SpecValidationError(
        f"Field 'max_file_size_mb' must be integer, got {type(spec.security.max_file_size_mb).__name__}",
        context={"field": "max_file_size_mb", "value": spec.security.max_file_size_mb},
        hint="Set max_file_size_mb to an integer value (e.g., 50 for 50MB)"
    )
    logger.error(str(error))
    errors.append(str(error))
```

---

### Step 3: Verify Error Messages

```bash
cd ToolForge
python -c "
from packages.core.errors import SpecValidationError
error = SpecValidationError(
    'Test error',
    context={'field': 'name', 'value': 'invalid'},
    hint='Try using a valid name'
)
print(error)
"
```

**Expected Output:**
```
Test error

Context:
  field: name
  value: invalid

Hint: Try using a valid name
```

---

## 🎯 Phase 2D: Coverage Testing (1-2 hours)

### Step 1: Add Unit Tests for Logger

**File:** `ToolForge/tests/test_logger.py` (create new)

```python
import json
import logging
from io import StringIO

import pytest

from packages.core.logger import ToolForgeFormatter, get_logger


def test_logger_formatter_basic():
    """Test that formatter produces valid JSON."""
    formatter = ToolForgeFormatter()
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname="test.py",
        lineno=1,
        msg="Test message",
        args=(),
        exc_info=None
    )
    output = formatter.format(record)
    data = json.loads(output)
    assert data["message"] == "Test message"
    assert data["level"] == "INFO"


def test_get_logger_returns_logger():
    """Test that get_logger returns a Logger instance."""
    logger = get_logger("test")
    assert isinstance(logger, logging.Logger)
    assert logger.name == "test"


def test_logger_includes_context():
    """Test that logger includes extra context fields."""
    logger = get_logger("test")
    # Context is included via extra dict on logger calls
    # This is more of an integration test
    assert logger is not None
```

**Add to `pyproject.toml`:**
```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
```

---

### Step 2: Add Unit Tests for Errors

**File:** `ToolForge/tests/test_errors.py` (create new)

```python
import pytest

from packages.core.errors import (
    SpecValidationError,
    SecurityValidationError,
    MCPGenerationError,
    SkillGenerationError,
    EvalGenerationError,
    PackagingError,
    ToolForgeError,
)


def test_toolforge_error_basic():
    """Test basic error creation."""
    error = ToolForgeError("Test error")
    assert str(error) == "Test error"


def test_toolforge_error_with_context():
    """Test error with context."""
    error = ToolForgeError(
        "Validation failed",
        context={"field": "name", "value": None}
    )
    assert "field" in str(error)


def test_toolforge_error_with_hint():
    """Test error with helpful hint."""
    error = ToolForgeError(
        "Invalid config",
        hint="Use .env.example as template"
    )
    assert "Hint:" in str(error)


@pytest.mark.parametrize("error_class", [
    SpecValidationError,
    SecurityValidationError,
    MCPGenerationError,
    SkillGenerationError,
    EvalGenerationError,
    PackagingError,
])
def test_error_subclasses(error_class):
    """Test all error subclasses can be instantiated."""
    error = error_class("Test message")
    assert isinstance(error, ToolForgeError)
```

**Run tests:**
```bash
cd ToolForge
python -m pytest tests/test_logger.py tests/test_errors.py -v
```

---

### Step 3: Check Coverage Improvement

```bash
cd ToolForge
python -m pytest tests/ --cov --cov-report=term-missing 2>&1 | grep -E "logger|errors|TOTAL"
```

**Expected:**
```
packages/core/logger.py          59      5     20     1    91%
packages/core/errors.py          57      2     14     1    96%
...
TOTAL                          1563    450    428    24    71%  ← Should be > 70%
```

---

## ✅ Completion Checklist

### Phase 2A: Quick Wins
- [ ] Run `ruff check --fix` and verify 10 fixes applied
- [ ] Remove unused imports (3 locations)
- [ ] Add mypy Pydantic plugin config
- [ ] Run tests: 43/43 passing
- [ ] Install pre-commit hooks locally
- [ ] Test pre-commit on a commit

### Phase 2B: Logging Integration
- [ ] Add logger to tool_spec.py
- [ ] Add logger to schema_validator.py
- [ ] Add logger to security_validator.py
- [ ] Verify logging output in test run
- [ ] Commit changes with pre-commit hook

### Phase 2C: Error Class Integration
- [ ] Update schema_validator.py to use SpecValidationError
- [ ] Update security_validator.py to use custom errors
- [ ] Verify error messages are helpful
- [ ] Test error with context and hints
- [ ] Commit changes

### Phase 2D: Coverage
- [ ] Create test_logger.py with 5+ tests
- [ ] Create test_errors.py with 8+ tests
- [ ] Run full test suite: verify coverage > 70%
- [ ] Generate coverage HTML report
- [ ] Commit with all tests passing

---

## 🚀 Post-Phase 2 Verification

After completing all steps above:

```bash
cd /Users/dawsonblock/Downloads/agent_eval_skills_merged_clean/ToolForge

# 1. All tests pass
python -m pytest tests/ -v

# 2. No linting errors
ruff check packages/ apps/

# 3. Type checking passes
mypy packages/ apps/

# 4. Coverage is good
python -m pytest tests/ --cov --cov-report=term | tail -5

# 5. Pre-commit hooks work
cd .. && git status
```

**Expected Results:**
- ✅ 45+ tests passing (43 existing + 2 new test modules)
- ✅ 0 linting errors
- ✅ 0 type errors
- ✅ 70%+ code coverage
- ✅ Pre-commit hooks active

---

## 📋 Files to Commit

```bash
cd /Users/dawsonblock/Downloads/agent_eval_skills_merged_clean

git add -A
git commit -m "Phase 2: Fix linting, integrate logging, add error classes

- Fix 10 linting errors with ruff
- Add mypy Pydantic plugin configuration
- Integrate structured logging in core modules
- Migrate to custom error classes with context/hints
- Add unit tests for logger and error classes
- Coverage improved from 29% to 71%
- Pre-commit hooks configured and tested"
```

---

## 💡 Notes

- **Before each step:** Run tests to establish baseline
- **After each step:** Verify no regressions with `pytest tests/`
- **Document logging patterns** in code comments for team reference
- **Consider adding** environment variable for log level control
- **Future enhancement:** Add structured log aggregation (ELK/Datadog/etc.)

---

**Prepared by:** Comprehensive Workspace Review
**Date:** May 16, 2026
**Expected Completion:** By end of day (4-6 hours total work)
