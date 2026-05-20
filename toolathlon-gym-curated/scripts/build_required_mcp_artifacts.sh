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
    if npm pkg get scripts.build | grep -qv null; then
      npm run build
    else
      echo "  - No build script for $name, skipping build step"
    fi
  )
}

build_python_package() {
  local pkg_dir="$1"
  local name="$2"

  if [ ! -f "$pkg_dir/pyproject.toml" ]; then
    echo "✗ Missing pyproject.toml for $name: $pkg_dir" >&2
    return 1
  fi

  if ! command -v uv >/dev/null 2>&1; then
    echo "✗ uv is required to build $name but was not found in PATH" >&2
    return 1
  fi

  echo "→ Building $name"
  (
    cd "$pkg_dir"
    uv sync
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
build_node_package "$LOCAL_SERVERS_DIR/mcp-canvas-lms" "canvas"
build_node_package "$LOCAL_SERVERS_DIR/HowToCook-mcp" "howtocook"
build_node_package "$LOCAL_SERVERS_DIR/servers/src/memory" "memory"
build_node_package "$LOCAL_SERVERS_DIR/google-forms-mcp" "google_forms"
build_node_package "$LOCAL_SERVERS_DIR/mcp-npx-fetch" "fetch"
build_node_package "$LOCAL_SERVERS_DIR/notion-mcp-server" "notion"
build_node_package "$LOCAL_SERVERS_DIR/woocommerce-mcp" "woocommerce"
build_node_package "$LOCAL_SERVERS_DIR/youtube-mcp-server" "youtube"
build_python_package "$LOCAL_SERVERS_DIR/mcp-youtube-transcript" "youtube_transcript"

ensure_file "$LOCAL_SERVERS_DIR/Calendar-Autoauth-MCP-Server/build/index.js" "google_calendar"
ensure_file "$LOCAL_SERVERS_DIR/mcp-canvas-lms/build/index.js" "canvas"
ensure_file "$LOCAL_SERVERS_DIR/HowToCook-mcp/build/index.js" "howtocook"
ensure_file "$LOCAL_SERVERS_DIR/servers/src/memory/dist/index.js" "memory"
ensure_file "$LOCAL_SERVERS_DIR/google-forms-mcp/build/index.js" "google_forms"
ensure_file "$LOCAL_SERVERS_DIR/mcp-npx-fetch/dist/index.js" "fetch"
ensure_file "$LOCAL_SERVERS_DIR/notion-mcp-server/bin/cli.mjs" "notion"
ensure_file "$LOCAL_SERVERS_DIR/woocommerce-mcp/dist/index.js" "woocommerce"
ensure_file "$LOCAL_SERVERS_DIR/youtube-mcp-server/dist/index.js" "youtube"
if [ -f "$LOCAL_SERVERS_DIR/mcp-youtube-transcript/.venv/bin/python3" ]; then
  echo "✓ youtube_transcript artifact: $LOCAL_SERVERS_DIR/mcp-youtube-transcript/.venv/bin/python3"
elif [ -f "$LOCAL_SERVERS_DIR/mcp-youtube-transcript/.venv/bin/python" ]; then
  echo "✓ youtube_transcript artifact: $LOCAL_SERVERS_DIR/mcp-youtube-transcript/.venv/bin/python"
else
  echo "✗ Missing youtube_transcript artifact after build: $LOCAL_SERVERS_DIR/mcp-youtube-transcript/.venv/bin/python3 or python" >&2
  exit 1
fi

echo "✓ Required MCP artifacts built successfully."
