#!/usr/bin/env bash
# Build the minimal set of MCP server artifacts required by preflight.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && cd .. && pwd)"
LOCAL_SERVERS_DIR="${LOCAL_SERVERS_PATH:-$ROOT_DIR/local_servers}"

echo "Using LOCAL_SERVERS_DIR=$LOCAL_SERVERS_DIR"

build_node_package() {
  local pkg_dir="$1"
  local name="$2"
  local artifact_path="$3"
  local start elapsed

  if [ ! -f "$pkg_dir/package.json" ]; then
    echo "✗ Missing package.json for $name: $pkg_dir" >&2
    return 1
  fi

  echo "→ Building $name"
  start="$(date +%s)"
  (
    cd "$pkg_dir"
    if [ -f package-lock.json ]; then
      npm ci --ignore-scripts
    else
      npm install --no-package-lock --ignore-scripts
    fi
    if npm pkg get scripts.build | grep -qv null; then
      npm run build
    else
      echo "  - No build script for $name, skipping build step"
    fi
  )
  ensure_file "$artifact_path" "$name"
  elapsed="$(( $(date +%s) - start ))"
  echo "✓ Built $name in ${elapsed}s"
}

build_python_package() {
  local pkg_dir="$1"
  local name="$2"
  local artifact_path="$3"
  local start elapsed

  if [ ! -f "$pkg_dir/pyproject.toml" ]; then
    echo "✗ Missing pyproject.toml for $name: $pkg_dir" >&2
    return 1
  fi

  if ! command -v uv >/dev/null 2>&1; then
    echo "✗ uv is required to build $name but was not found in PATH" >&2
    return 1
  fi

  echo "→ Building $name"
  start="$(date +%s)"
  (
    cd "$pkg_dir"
    uv sync
  )
  if [ -x "$pkg_dir/.venv/bin/python" ] && [ ! -e "$pkg_dir/.venv/bin/python3" ]; then
    ln -s python "$pkg_dir/.venv/bin/python3"
  fi
  ensure_file "$artifact_path" "$name"
  elapsed="$(( $(date +%s) - start ))"
  echo "✓ Built $name in ${elapsed}s"
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

build_node_package "$LOCAL_SERVERS_DIR/Calendar-Autoauth-MCP-Server" "google_calendar" "$LOCAL_SERVERS_DIR/Calendar-Autoauth-MCP-Server/build/index.js"
build_node_package "$LOCAL_SERVERS_DIR/mcp-canvas-lms" "canvas" "$LOCAL_SERVERS_DIR/mcp-canvas-lms/build/index.js"
build_node_package "$LOCAL_SERVERS_DIR/HowToCook-mcp" "howtocook" "$LOCAL_SERVERS_DIR/HowToCook-mcp/build/index.js"
build_node_package "$LOCAL_SERVERS_DIR/servers/src/memory" "memory" "$LOCAL_SERVERS_DIR/servers/src/memory/dist/index.js"
build_node_package "$LOCAL_SERVERS_DIR/google-forms-mcp" "google_forms" "$LOCAL_SERVERS_DIR/google-forms-mcp/build/index.js"
build_node_package "$LOCAL_SERVERS_DIR/mcp-npx-fetch" "fetch" "$LOCAL_SERVERS_DIR/mcp-npx-fetch/dist/index.js"
build_node_package "$LOCAL_SERVERS_DIR/notion-mcp-server" "notion" "$LOCAL_SERVERS_DIR/notion-mcp-server/bin/cli.mjs"
build_node_package "$LOCAL_SERVERS_DIR/woocommerce-mcp" "woocommerce" "$LOCAL_SERVERS_DIR/woocommerce-mcp/dist/index.js"
build_node_package "$LOCAL_SERVERS_DIR/youtube-mcp-server" "youtube" "$LOCAL_SERVERS_DIR/youtube-mcp-server/dist/index.js"
build_python_package "$LOCAL_SERVERS_DIR/mcp-youtube-transcript" "youtube_transcript" "$LOCAL_SERVERS_DIR/mcp-youtube-transcript/.venv/bin/python3"

echo "✓ Required MCP artifacts built successfully."
