---
name: refactor-cli-tests-and-environment
description: Workflow command scaffold for refactor-cli-tests-and-environment in agent_eval_skills_merged_clean.
allowed_tools: ["Bash", "Read", "Write", "Grep", "Glob"]
---

# /refactor-cli-tests-and-environment

Use this workflow when working on **refactor-cli-tests-and-environment** in `agent_eval_skills_merged_clean`.

## Goal

Refactor CLI-related test files to improve reliability, speed, and environment setup. This includes switching to more robust fixtures, removing subprocess-based setup in favor of internal Python APIs, and ensuring consistent environment variables.

## Common Files

- `ToolForge/tests/test_cli_command_exit.py`
- `ToolForge/tests/test_registry_cli_exit.py`
- `scripts/demo_csv_cleaner.sh`

## Suggested Sequence

1. Understand the current state and failure mode before editing.
2. Make the smallest coherent change that satisfies the workflow goal.
3. Run the most relevant verification for touched files.
4. Summarize what changed and what still needs review.

## Typical Commit Signals

- Update test_cli_command_exit.py to use improved fixtures or internal APIs instead of subprocesses.
- Update test_registry_cli_exit.py similarly for registry CLI tests.
- Adjust or add helper functions (e.g., _cli, _build_env) to centralize environment setup.
- Optionally, update related scripts (e.g., demo_csv_cleaner.sh) to ensure correct environment variables.
- Update documentation or remove unstable test prompts as needed.

## Notes

- Treat this as a scaffold, not a hard-coded script.
- Update the command if the workflow evolves materially.