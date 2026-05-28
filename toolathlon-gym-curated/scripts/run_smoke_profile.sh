#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
REPO_ROOT="$(cd "$ROOT_DIR/.." && pwd)"

mkdir -p "$REPO_ROOT/release_artifacts/validation_logs"

python3 "$ROOT_DIR/scripts/preflight_mcp_paths.py" \
  --profile smoke \
  --json-output "$REPO_ROOT/release_artifacts/validation_logs/toolathlon_preflight_summary.json"

python3 "$ROOT_DIR/scripts/smoke_mcp_servers.py" \
  --profile smoke \
  --strict \
  --json-output "$REPO_ROOT/release_artifacts/validation_logs/toolathlon_smoke_summary.json"