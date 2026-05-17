"""Test configuration and process-state isolation for pytest runs."""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

# Add ToolForge root to path so `from packages.core...` works in pytest.
toolforge_root = Path(__file__).parent.parent
if str(toolforge_root) not in sys.path:
    sys.path.insert(0, str(toolforge_root))


@pytest.fixture(autouse=True)
def restore_process_state() -> None:
    """Prevent process-global leakage between tests (cwd/env/argv/sys.path)."""
    original_cwd = Path.cwd()
    original_argv = sys.argv[:]
    original_env = os.environ.copy()
    original_syspath = sys.path[:]
    try:
        yield
    finally:
        os.chdir(original_cwd)
        sys.argv[:] = original_argv
        sys.path[:] = original_syspath
        os.environ.clear()
        os.environ.update(original_env)
