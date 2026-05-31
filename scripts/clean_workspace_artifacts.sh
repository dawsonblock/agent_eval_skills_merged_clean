#!/usr/bin/env bash
set -euo pipefail
echo "[clean] Removing macOS metadata..."
find . -name ".DS_Store" -delete
find . -name "._*" -delete
rm -rf __MACOSX
echo "[clean] Removing transient Python/cache artifacts..."
find . -type d -name "__pycache__" -prune -exec rm -rf {} +
find . -type f -name "*.pyc" -delete
find . -type f -name "*.pyo" -delete
find . -type d -name ".pytest_cache" -prune -exec rm -rf {} +
echo "[clean] Removing transient frontend artifacts..."
find . -type d -name ".vite" -prune -exec rm -rf {} +
find . -type d -name ".turbo" -prune -exec rm -rf {} +
echo "[clean] Done."
