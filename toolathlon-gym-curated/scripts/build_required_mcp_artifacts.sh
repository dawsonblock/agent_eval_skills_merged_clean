#!/usr/bin/env bash
# Build the minimal set of MCP server artifacts required by preflight.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && cd .. && pwd)"
LOCAL_SERVERS_DIR="${LOCAL_SERVERS_PATH:-$ROOT_DIR/local_servers}"

echo "Using LOCAL_SERVERS_DIR=$LOCAL_SERVERS_DIR"

build_node_package() {
  local pkg_dir="$1"
  local name="$2"

  if [ ! -d "$pkg_dir" ]; then
    echo "✗ Missing package directory for $name: $pkg_dir" >&2
    return 1
  fi

  echo "→ Building $name"
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
}

ensure_python3_link() {
  local venv_bin="$1/.venv/bin"
  if [ -x "$venv_bin/python" ] && [ ! -e "$venv_bin/python3" ]; then
    ln -s python "$venv_bin/python3"
  fi
}

build_python_uv_package() {
  local pkg_dir="$1"
  local name="$2"

  if [ ! -d "$pkg_dir" ]; then
    echo "✗ Missing Python package directory for $name: $pkg_dir" >&2
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
  ensure_python3_link "$pkg_dir"
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

export -f build_node_package
export -f build_python_uv_package
export -f ensure_python3_link
export -f ensure_file

build_with_timeout() {
  local name="$1"
  local seconds="$2"
  shift 2

  echo "→ Building $name with ${seconds}s timeout"
  local start
  start="$(date +%s)"

  if command -v timeout >/dev/null 2>&1; then
    if ! timeout "${seconds}s" bash -lc 'set -euo pipefail; "$@"' _ "$@"; then
      echo "✗ Build failed or timed out: $name" >&2
      return 1
    fi
  else
    if ! python3 - "$seconds" "$@" <<'PY'
import subprocess
import sys

timeout = int(sys.argv[1])
command = sys.argv[2:]

try:
    completed = subprocess.run(["bash", "-lc", "set -euo pipefail; \"$@\"", "_", *command], check=False, timeout=timeout)
except subprocess.TimeoutExpired:
    raise SystemExit(124)
raise SystemExit(completed.returncode)
PY
    then
      echo "✗ Build failed or timed out: $name" >&2
      return 1
    fi
  fi

  local elapsed
  elapsed="$(( $(date +%s) - start ))"
  echo "✓ Built $name in ${elapsed}s"
}

echo "Building required MCP artifacts in $LOCAL_SERVERS_DIR"
build_with_timeout "google_calendar" 180 build_node_package "$LOCAL_SERVERS_DIR/Calendar-Autoauth-MCP-Server" "google_calendar" || exit 1
ensure_file "$LOCAL_SERVERS_DIR/Calendar-Autoauth-MCP-Server/build/index.js" "google_calendar" || exit 1
build_with_timeout "canvas" 900 build_node_package "$LOCAL_SERVERS_DIR/mcp-canvas-lms" "canvas" || exit 1
ensure_file "$LOCAL_SERVERS_DIR/mcp-canvas-lms/build/index.js" "canvas" || exit 1
build_with_timeout "howtocook" 300 build_node_package "$LOCAL_SERVERS_DIR/HowToCook-mcp" "howtocook" || exit 1
ensure_file "$LOCAL_SERVERS_DIR/HowToCook-mcp/build/index.js" "howtocook" || exit 1
build_with_timeout "memory" 300 build_node_package "$LOCAL_SERVERS_DIR/servers/src/memory" "memory" || exit 1
ensure_file "$LOCAL_SERVERS_DIR/servers/src/memory/dist/index.js" "memory" || exit 1
build_with_timeout "google_forms" 300 build_node_package "$LOCAL_SERVERS_DIR/google-forms-mcp" "google_forms" || exit 1
ensure_file "$LOCAL_SERVERS_DIR/google-forms-mcp/build/index.js" "google_forms" || exit 1
build_with_timeout "fetch" 300 build_node_package "$LOCAL_SERVERS_DIR/mcp-npx-fetch" "fetch" || exit 1
ensure_file "$LOCAL_SERVERS_DIR/mcp-npx-fetch/dist/index.js" "fetch" || exit 1
build_with_timeout "notion" 900 build_node_package "$LOCAL_SERVERS_DIR/notion-mcp-server" "notion" || exit 1
ensure_file "$LOCAL_SERVERS_DIR/notion-mcp-server/bin/cli.mjs" "notion" || exit 1
build_with_timeout "woocommerce" 300 build_node_package "$LOCAL_SERVERS_DIR/woocommerce-mcp" "woocommerce" || exit 1
ensure_file "$LOCAL_SERVERS_DIR/woocommerce-mcp/dist/index.js" "woocommerce" || exit 1
build_with_timeout "youtube" 600 build_node_package "$LOCAL_SERVERS_DIR/youtube-mcp-server" "youtube" || exit 1
ensure_file "$LOCAL_SERVERS_DIR/youtube-mcp-server/dist/index.js" "youtube" || exit 1
build_with_timeout "youtube_transcript" 900 build_python_uv_package "$LOCAL_SERVERS_DIR/mcp-youtube-transcript" "youtube_transcript" || exit 1
ensure_file "$LOCAL_SERVERS_DIR/mcp-youtube-transcript/.venv/bin/python3" "youtube_transcript" || exit 1

python scripts/preflight_mcp_paths.py

echo "✓ Required MCP artifacts built successfully."
