"""Consolidated process-tree timeout helper for subprocess execution."""
from __future__ import annotations

# Re-export from packages.core for test compatibility
from packages.core.process_timeout import run_with_process_tree_timeout

__all__ = ["run_with_process_tree_timeout"]
