#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
TOOLATHLON_DIR="$ROOT/toolathlon-gym-curated"
LOG_DIR="$ROOT/.validation_logs"

cd "$TOOLATHLON_DIR"

export TOOLATHLON_PROFILE=smoke

mkdir -p "$LOG_DIR"

python scripts/preflight_mcp_paths.py \
	--json-output "$LOG_DIR/toolathlon_smoke_preflight.json"

python scripts/smoke_mcp_servers.py \
	--profile smoke \
	--json-output "$LOG_DIR/toolathlon_mcp_smoke_summary.json"

echo "Toolathlon smoke profile checks completed."
