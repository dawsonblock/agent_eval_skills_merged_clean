#!/usr/bin/env bash
set -euo pipefail

echo "Toolathlon smoke profile uses pre-vendored servers (rail_12306, filesystem)."
echo "No dependency install step is required for smoke profile validation."
echo "For local development of the MCP servers workspace, run:"
echo "  cd toolathlon-gym-curated/local_servers/12306-mcp && npm ci && npm run build"
echo "  cd toolathlon-gym-curated/local_servers/filesystem && npm ci && npm run build"
