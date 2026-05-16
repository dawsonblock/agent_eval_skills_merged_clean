# Legacy Inventory

This document records what legacy content is intentionally kept in the current ToolForge workspace and what was removed during the cleanup pass.

## Kept

- `agent-skills-curated/` at the repository root.
- `toolathlon-gym-curated/` at the repository root.
- `ToolForge/` as the active ToolForge workspace.
- ToolForge-generated examples that are used as the current proof path, including the CSV cleaner scaffold.
- The full curated task and skill catalogs remain in their single top-level copies to preserve benchmark reproducibility and skill evaluation coverage.

## Removed

- `ToolForge/legacy/` duplicated copies of the legacy repositories.
- Generated cache and run artifacts such as `__pycache__/`, `*.pyc`, `.coverage`, `.pytest_cache/`, and `htmlcov/` when they appear in the workspace.
- Stale package outputs, logs, and other derived artifacts that do not belong in source control.

## Deferred pruning (intentional)

- Large benchmark/task datasets under `toolathlon-gym-curated/tasks/` are retained for reproducibility and were not trimmed in this pass.
- MCP local server sources under `toolathlon-gym-curated/local_servers/` are retained as benchmark dependencies even when individual servers are not used by the CSV proof path.
- Curated skill packs under `agent-skills-curated/skills/` are retained in full in this pass; selective category pruning is deferred to a dedicated curation pass.

## Why

The repository is intended to keep one active copy of each top-level curated repository and one active ToolForge workspace. Duplicate legacy trees make review, packaging, and hygiene checks harder without adding runtime value.

This pass prioritized CSV proof-path stability and workspace integrity over broad benchmark-content deletion.

## How to restore a removed legacy copy

If a future workflow needs the full original archive layout, restore the legacy tree from the upstream zip or source snapshot before running any cleanup scripts. Do not reintroduce duplicated legacy trees into the active source layout unless a task explicitly requires that archival structure.
