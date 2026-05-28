#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_DIR="$ROOT/../release_artifacts/validation_logs"
mkdir -p "$LOG_DIR"

cd "$ROOT"
python scripts/preflight_mcp_paths.py \
  --profile smoke \
  --json-output "$LOG_DIR/toolathlon_preflight_smoke_summary.json" \
  | tee "$LOG_DIR/toolathlon_preflight_smoke.txt"

python scripts/smoke_mcp_servers.py \
  --profile smoke \
  --json-output "$LOG_DIR/toolathlon_smoke_summary.json" \
  | tee "$LOG_DIR/toolathlon_smoke.txt"
echo "PASS: Toolathlon smoke profile passed"