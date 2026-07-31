---
name: prevent-subprocess-hangs-in-cli-and-tests
description: Workflow command scaffold for prevent-subprocess-hangs-in-cli-and-tests in agent_eval_skills_merged_clean.
allowed_tools: ["Bash", "Read", "Write", "Grep", "Glob"]
---

# /prevent-subprocess-hangs-in-cli-and-tests

Use this workflow when working on **prevent-subprocess-hangs-in-cli-and-tests** in `agent_eval_skills_merged_clean`.

## Goal

Refactor CLI and test code to prevent subprocess hangs by switching from subprocess calls to internal Python APIs and ensuring explicit process termination.

## Common Files

- `ToolForge/tests/test_cli_command_exit.py`
- `ToolForge/tests/test_registry_cli_exit.py`
- `ToolForge/apps/cli/toolforge_cli/main.py`

## Suggested Sequence

1. Understand the current state and failure mode before editing.
2. Make the smallest coherent change that satisfies the workflow goal.
3. Run the most relevant verification for touched files.
4. Summarize what changed and what still needs review.

## Typical Commit Signals

- Refactor test files to use internal Python API calls instead of subprocess-based setup.
- Update CLI main entrypoints (e.g., registry_info) to include explicit sys.exit(0) for clean termination.
- Remove unstable or AI-generated prompts from test setup.
- Update or add documentation as needed.

## Notes

- Treat this as a scaffold, not a hard-coded script.
- Update the command if the workflow evolves materially.