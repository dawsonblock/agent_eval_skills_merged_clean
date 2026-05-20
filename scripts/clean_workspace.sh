#!/usr/bin/env bash
# Clean workspace caches for fresh validation/testing
# Removes: __pycache__, .pytest_cache, .mypy_cache, .ruff_cache

set -euo pipefail

echo "Cleaning workspace caches..."

find . -type d -name "__pycache__" -prune -exec rm -rf {} + 2>/dev/null || true
find . -type d -name ".pytest_cache" -prune -exec rm -rf {} + 2>/dev/null || true
find . -type d -name ".mypy_cache" -prune -exec rm -rf {} + 2>/dev/null || true
find . -type d -name ".ruff_cache" -prune -exec rm -rf {} + 2>/dev/null || true

echo "✓ Workspace caches removed."
