"""Test configuration and process-state isolation for pytest runs."""
from __future__ import annotations

import logging
import os
import signal
import subprocess
import sys
import time
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


def _collect_descendant_toolforge_pids() -> list[int]:
    """Find descendant ToolForge child processes for this pytest worker only."""
    patterns = (
        "python -m apps.cli.toolforge_cli.main",
        "/tools/generated/",
        "/tool.py",
    )
    try:
        ps_result = subprocess.run(
            ["ps", "-axo", "pid=,ppid=,command="],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return []

    children_by_parent: dict[int, list[int]] = {}
    command_by_pid: dict[int, str] = {}

    for line in ps_result.stdout.splitlines():
        parts = line.strip().split(None, 2)
        if len(parts) < 3:
            continue
        try:
            pid = int(parts[0])
            ppid = int(parts[1])
        except ValueError:
            continue
        cmd = parts[2]
        children_by_parent.setdefault(ppid, []).append(pid)
        command_by_pid[pid] = cmd

    descendants: set[int] = set()
    stack = [os.getpid()]
    while stack:
        parent = stack.pop()
        for child in children_by_parent.get(parent, []):
            if child in descendants:
                continue
            descendants.add(child)
            stack.append(child)

    matched: list[int] = []
    for pid in sorted(descendants):
        cmd = command_by_pid.get(pid, "").lower()
        if any(pattern in cmd for pattern in patterns):
            matched.append(pid)
    return matched


def _terminate_pids(pids: list[int]) -> None:
    if not pids:
        return

    for pid in pids:
        try:
            os.kill(pid, signal.SIGTERM)
        except ProcessLookupError:
            continue

    time.sleep(0.5)

    for pid in pids:
        try:
            os.kill(pid, signal.SIGKILL)
        except ProcessLookupError:
            continue


@pytest.fixture(autouse=True)
def cleanup_toolforge_child_processes() -> None:
    """Ensure descendant ToolForge child processes do not leak between tests."""
    try:
        yield
    finally:
        _terminate_pids(_collect_descendant_toolforge_pids())
