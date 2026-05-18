"""Test configuration and process-state isolation for pytest runs."""
from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

import pytest

# Add ToolForge root to path so `from packages.core...` works in pytest.
toolforge_root = Path(__file__).parent.parent
if str(toolforge_root) not in sys.path:
    sys.path.insert(0, str(toolforge_root))


def pytest_configure(config: pytest.Config) -> None:
    """Configure pytest markers."""
    config.addinivalue_line(
        "markers", "e2e_isolated: mark test as requiring process isolation"
    )


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


@pytest.fixture(autouse=True)
def restore_logging_state() -> None:
    """Prevent logging handler/level leakage between tests."""
    root = logging.getLogger()
    original_handlers = root.handlers[:]
    original_level = root.level
    try:
        yield
    finally:
        root.handlers[:] = original_handlers
        root.setLevel(original_level)
