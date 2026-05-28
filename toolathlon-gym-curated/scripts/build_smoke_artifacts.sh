#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_DIR="$ROOT/../release_artifacts/validation_logs"
mkdir -p "$LOG_DIR"
echo '{ "profile": "smoke", "servers": {} }' > "$LOG_DIR/toolathlon_build_smoke_summary.json"

build_server() {
  local name="$1"
  local dir=""
  case "$name" in
    rail_12306) dir="$ROOT/local_servers/12306-mcp" ;;
    filesystem) dir="$ROOT/local_servers/filesystem" ;;
    *)
      echo "FAIL: unknown smoke server mapping: $name"
      exit 1
      ;;
  esac

  echo "Building smoke server: $name"
  if [ ! -d "$dir" ]; then
    echo "FAIL: missing server directory: $dir"
    exit 1
  fi

  cd "$dir"
  if [ -f package-lock.json ]; then
    npm ci
  elif [ -f package.json ]; then
    npm install
  else
    echo "FAIL: missing package.json for $name"
    exit 1
  fi

  if npm run | grep -q " build"; then
    npm run build
  fi
  cd "$ROOT"
}

build_server "rail_12306"
build_server "filesystem"
echo "PASS: smoke artifacts built"