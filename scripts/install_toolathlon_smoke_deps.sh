#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
SERVERS_DIR="$ROOT/toolathlon-gym-curated/local_servers/servers"

if [[ ! -d "$SERVERS_DIR" ]]; then
  echo "Missing local servers directory: $SERVERS_DIR" >&2
  exit 1
fi

cd "$SERVERS_DIR"

if [[ ! -f package.json ]]; then
  echo "Missing package.json in $SERVERS_DIR" >&2
  exit 1
fi

if [[ -f package-lock.json ]]; then
  npm ci
else
  npm install
fi

if npm run | grep -q " build"; then
  npm run build
fi

echo "Toolathlon smoke dependencies installed for local servers: rail_12306, filesystem"
