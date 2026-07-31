```markdown
# agent_eval_skills_merged_clean Development Patterns

> Auto-generated skill from repository analysis

## Overview

This skill teaches best practices and workflows for contributing to the `agent_eval_skills_merged_clean` Python codebase. The repository focuses on robust CLI tools and their testing, emphasizing reliable, maintainable, and deterministic test environments. You will learn coding conventions, test patterns, and step-by-step workflows for refactoring CLI-related code and preventing subprocess hangs.

## Coding Conventions

- **File Naming:**  
  Use `snake_case` for all file and module names.  
  _Example:_  
  ```
  test_cli_command_exit.py
  registry_info.py
  ```

- **Import Style:**  
  Prefer **relative imports** within packages.  
  _Example:_  
  ```python
  from .utils import build_env
  ```

- **Export Style:**  
  Use **named exports** (explicitly define what is exported from a module).  
  _Example:_  
  ```python
  __all__ = ["run_cli", "parse_args"]
  ```

- **Commit Messages:**  
  Follow the **Conventional Commits** style with prefixes like `refactor`, `test`, `fix`.  
  _Example:_  
  ```
  refactor: use internal API for CLI test setup
  test: add fixture for registry CLI exit test
  fix: ensure sys.exit(0) in main CLI entrypoint
  ```

## Workflows

### Refactor CLI Tests and Environment
**Trigger:** When you want to improve the robustness, speed, or determinism of CLI-related tests, especially to prevent hangs or redundant workspace setup.  
**Command:** `/refactor-cli-tests`

1. Update `test_cli_command_exit.py` to use improved fixtures or internal APIs instead of subprocesses.
2. Update `test_registry_cli_exit.py` similarly for registry CLI tests.
3. Adjust or add helper functions (e.g., `_cli`, `_build_env`) to centralize environment setup.
4. Optionally, update related scripts (e.g., `demo_csv_cleaner.sh`) to ensure correct environment variables.
5. Update documentation or remove unstable test prompts as needed.

_Example: Refactoring a test to use internal APIs_
```python
# Before: using subprocess
import subprocess

def test_cli_exit():
    result = subprocess.run(["python", "main.py"], capture_output=True)
    assert result.returncode == 0

# After: using internal API
from ToolForge.apps.cli.toolforge_cli.main import main

def test_cli_exit():
    assert main() == 0
```

### Prevent Subprocess Hangs in CLI and Tests
**Trigger:** When you encounter or want to prevent test or CLI subprocesses from hanging, especially in exit scenarios.  
**Command:** `/fix-cli-hangs`

1. Refactor test files to use internal Python API calls instead of subprocess-based setup.
2. Update CLI main entrypoints (e.g., `registry_info`) to include explicit `sys.exit(0)` for clean termination.
3. Remove unstable or AI-generated prompts from test setup.
4. Update or add documentation as needed.

_Example: Ensuring clean CLI termination_
```python
import sys

def main():
    # ... CLI logic ...
    sys.exit(0)
```

## Testing Patterns

- **Test File Naming:**  
  Test files use the pattern `*.test.*` and are named with `snake_case`.

- **Test Framework:**  
  The specific test framework is not detected, but tests are written as Python functions, likely using `pytest` or similar.

- **Fixtures and Helpers:**  
  Prefer using robust fixtures and internal APIs over subprocess calls for setting up and tearing down test environments.

_Example: Using a fixture for environment setup_
```python
import pytest

@pytest.fixture
def cli_env():
    # Setup code
    yield
    # Teardown code

def test_cli_command(cli_env):
    # Test code using the fixture
```

## Commands

| Command              | Purpose                                                        |
|----------------------|----------------------------------------------------------------|
| /refactor-cli-tests  | Refactor CLI-related tests for reliability and speed           |
| /fix-cli-hangs       | Refactor CLI/tests to prevent subprocess hangs and ensure clean exits |
```
