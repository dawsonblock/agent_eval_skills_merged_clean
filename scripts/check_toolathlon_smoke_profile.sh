#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
TOOLATHLON_DIR="$ROOT/toolathlon-gym-curated"

cd "$TOOLATHLON_DIR"

export TOOLATHLON_PROFILE=smoke

python scripts/preflight_mcp_paths.py --profile smoke
python scripts/smoke_mcp_servers.py --profile smoke

echo "Toolathlon smoke profile checks completed."
