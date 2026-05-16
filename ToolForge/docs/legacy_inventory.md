# Legacy Inventory

This document records what legacy content is intentionally kept in the current ToolForge workspace and what was removed during the cleanup pass.

## Kept

- `agent-skills-curated/` at the repository root.
- `toolathlon-gym-curated/` at the repository root.
- `ToolForge/` as the active ToolForge workspace.
- ToolForge-generated examples that are used as the current proof path, including the CSV cleaner scaffold.

## Removed

- `ToolForge/legacy/` duplicated copies of the legacy repositories.
- Generated cache and run artifacts such as `__pycache__/`, `*.pyc`, `.coverage`, `.pytest_cache/`, and `htmlcov/` when they appear in the workspace.
- Stale package outputs, logs, and other derived artifacts that do not belong in source control.

## Why

The repository is intended to keep one active copy of each top-level curated repository and one active ToolForge workspace. Duplicate legacy trees make review, packaging, and hygiene checks harder without adding runtime value.

## How to restore a removed legacy copy

If a future workflow needs the full original archive layout, restore the legacy tree from the upstream zip or source snapshot before running any cleanup scripts. Do not reintroduce duplicated legacy trees into the active source layout unless a task explicitly requires that archival structure.
