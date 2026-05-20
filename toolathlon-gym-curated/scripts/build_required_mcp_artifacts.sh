#!/usr/bin/env bash
# Build the minimal set of MCP server artifacts required by preflight.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && cd .. && pwd)"
LOCAL_SERVERS_DIR="$ROOT_DIR/local_servers"

build_node_package() {
  local pkg_dir="$1"
  local name="$2"

  if [ ! -f "$pkg_dir/package.json" ]; then
    echo "✗ Missing package.json for $name: $pkg_dir" >&2
    return 1
  fi

  echo "→ Building $name"
  (
    cd "$pkg_dir"
    npm install
    npm run build
  )
}

ensure_file() {
  local file_path="$1"
  local label="$2"

  if [ -f "$file_path" ]; then
    echo "✓ $label artifact: $file_path"
  else
    echo "✗ Missing $label artifact after build: $file_path" >&2
    return 1
  fi
}

echo "Building required MCP artifacts in $LOCAL_SERVERS_DIR"

build_node_package "$LOCAL_SERVERS_DIR/Calendar-Autoauth-MCP-Server" "google_calendar"
build_node_package "$LOCAL_SERVERS_DIR/google-forms-mcp" "google_forms"
build_node_package "$LOCAL_SERVERS_DIR/youtube-mcp-server" "youtube"

ensure_file "$LOCAL_SERVERS_DIR/Calendar-Autoauth-MCP-Server/build/index.js" "google_calendar"
ensure_file "$LOCAL_SERVERS_DIR/google-forms-mcp/build/index.js" "google_forms"
ensure_file "$LOCAL_SERVERS_DIR/youtube-mcp-server/dist/index.js" "youtube"

echo "✓ Required MCP artifacts built successfully."
