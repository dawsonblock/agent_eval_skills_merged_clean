#!/usr/bin/env bash
# Shared forbidden-entry policy for release and evidence ZIP hygiene checks.

set -euo pipefail

# Matches zip entry paths produced by `zipinfo -1`.
RELEASE_FORBIDDEN_ENTRY_REGEX='(^|/)(__MACOSX/|\._|\.DS_Store$|node_modules/|\.validation_logs/|__pycache__/|\.pytest_cache/|\.mypy_cache/|\.ruff_cache/|\.venv/)'
