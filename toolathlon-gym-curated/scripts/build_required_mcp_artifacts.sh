#!/usr/bin/env bash
# Build the minimal set of MCP server artifacts required by preflight.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && cd .. && pwd)"
LOCAL_SERVERS_DIR="${LOCAL_SERVERS_PATH:-$ROOT_DIR/local_servers}"
SKIP_EXISTING_ARTIFACTS="${SKIP_EXISTING_ARTIFACTS:-0}"
FORCE_REBUILD="${FORCE_REBUILD:-0}"
BUILD_SUMMARY_FILE="${ROOT_DIR}/../.validation_logs/toolathlon_artifact_build_summary.json"

echo "Using LOCAL_SERVERS_DIR=$LOCAL_SERVERS_DIR"
echo "SKIP_EXISTING_ARTIFACTS=$SKIP_EXISTING_ARTIFACTS"
echo "FORCE_REBUILD=$FORCE_REBUILD"

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

  if [ ! -f "$file_path" ] && [ ! -x "$file_path" ]; then
    echo "✗ Missing $label artifact after build:" >&2
    echo "  $file_path" >&2
    return 1
  fi

    echo "✓ $label artifact: $file_path"
}

export -f build_node_package
export -f build_python_uv_package
export -f ensure_python3_link

artifact_exists() {
  local path="$1"
  [ -f "$path" ] || [ -x "$path" ]
}

# Initialize JSON output
init_build_summary() {
  mkdir -p "$(dirname "$BUILD_SUMMARY_FILE")"
  cat >"$BUILD_SUMMARY_FILE" <<'EOF'
{
  "overall_status": "in_progress",
  "package_count": 0,
  "passed_count": 0,
  "failed_count": 0,
  "packages": []
}
EOF
}

# Append a package result to JSON
record_package_result() {
  local name="$1"
  local status="$2"
  local duration="$3"
  local artifact="$4"
  local skipped_existing="${5:-false}"
  local reason="${6:-}"

  python3 - "$BUILD_SUMMARY_FILE" "$name" "$status" "$duration" "$artifact" "$skipped_existing" "$reason" <<'PYEOF'
import sys, json

summary_file = sys.argv[1]
name = sys.argv[2]
status = sys.argv[3]
duration = int(sys.argv[4])
artifact = sys.argv[5]
skipped_existing = sys.argv[6] == 'true'
reason = sys.argv[7] if len(sys.argv) > 7 and sys.argv[7] else None

with open(summary_file, 'r') as f:
    data = json.load(f)

entry = {
    "package": name,
    "status": status,
    "duration_seconds": duration,
    "artifact": artifact,
    "skipped_existing": skipped_existing,
}
if reason:
    entry["reason"] = reason

data['packages'].append(entry)
data['package_count'] = len(data['packages'])

if status == 'passed':
    data['passed_count'] += 1
elif status == 'failed':
    data['failed_count'] += 1

if data['failed_count'] > 0:
    data['overall_status'] = 'failed'
else:
    data['overall_status'] = 'passed'

with open(summary_file, 'w') as f:
    json.dump(data, f, indent=2)
PYEOF
}

build_with_timeout() {
  local name="$1"
  local seconds="$2"
  shift 2

  echo "→ Building $name with ${seconds}s timeout"
  local start
  start="$(date +%s)"

  if command -v timeout >/dev/null 2>&1; then
    if ! timeout "${seconds}s" bash -lc 'set -euo pipefail; "$@"' _ "$@"; then
      local elapsed
      elapsed="$(( $(date +%s) - start ))"
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
      local elapsed
      elapsed="$(( $(date +%s) - start ))"
      echo "✗ Build failed or timed out: $name" >&2
      return 1
    fi
  fi

  local elapsed
  elapsed="$(( $(date +%s) - start ))"
  echo "✓ Built $name in ${elapsed}s"
}

# Helper to build a package, respecting skip/rebuild flags
maybe_build_node_package() {
  local name="$1"
  local timeout_sec="$2"
  local pkg_dir="$3"
  local artifact="$4"
  local start
  start="$(date +%s)"

  if [ "${FORCE_REBUILD:-0}" = "1" ]; then
    echo "→ Force rebuild requested for $name"
    build_with_timeout "$name" "$timeout_sec" build_node_package "$pkg_dir" "$name" || return 1
  elif [ "${SKIP_EXISTING_ARTIFACTS:-0}" = "1" ] && artifact_exists "$artifact"; then
    local elapsed
    elapsed="$(( $(date +%s) - start ))"
    echo "✓ $name artifact already exists: $artifact (skipped)"
    record_package_result "$name" "passed" "$elapsed" "$artifact" "true"
    return 0
  else
    build_with_timeout "$name" "$timeout_sec" build_node_package "$pkg_dir" "$name" || return 1
  fi

  local elapsed
  elapsed="$(( $(date +%s) - start ))"
  record_package_result "$name" "passed" "$elapsed" "$artifact"
}

maybe_build_python_package() {
  local name="$1"
  local timeout_sec="$2"
  local pkg_dir="$3"
  local artifact="$4"
  local start
  start="$(date +%s)"

  if [ "${FORCE_REBUILD:-0}" = "1" ]; then
    echo "→ Force rebuild requested for $name"
    build_with_timeout "$name" "$timeout_sec" build_python_uv_package "$pkg_dir" "$name" || return 1
  elif [ "${SKIP_EXISTING_ARTIFACTS:-0}" = "1" ] && artifact_exists "$artifact"; then
    local elapsed
    elapsed="$(( $(date +%s) - start ))"
    echo "✓ $name artifact already exists: $artifact (skipped)"
    record_package_result "$name" "passed" "$elapsed" "$artifact" "true"
    return 0
  else
    build_with_timeout "$name" "$timeout_sec" build_python_uv_package "$pkg_dir" "$name" || return 1
  fi

  local elapsed
  elapsed="$(( $(date +%s) - start ))"
  record_package_result "$name" "passed" "$elapsed" "$artifact"
}

echo "Building required MCP artifacts in $LOCAL_SERVERS_DIR"

# Initialize JSON summary
init_build_summary

# Build each package, recording results
maybe_build_node_package "rail_12306" 300 "$LOCAL_SERVERS_DIR/12306-mcp" "$LOCAL_SERVERS_DIR/12306-mcp/build/index.js" || {
  record_package_result "rail_12306" "failed" 300 "$LOCAL_SERVERS_DIR/12306-mcp/build/index.js" "false" "build_error"
  exit 1
}
ensure_file "$LOCAL_SERVERS_DIR/12306-mcp/build/index.js" "rail_12306" || exit 1

maybe_build_node_package "filesystem" 300 "$LOCAL_SERVERS_DIR/filesystem" "$LOCAL_SERVERS_DIR/filesystem/dist/index.js" || {
  record_package_result "filesystem" "failed" 300 "$LOCAL_SERVERS_DIR/filesystem/dist/index.js" "false" "build_error"
  exit 1
}
ensure_file "$LOCAL_SERVERS_DIR/filesystem/dist/index.js" "filesystem" || exit 1

maybe_build_node_package "google_calendar" 180 "$LOCAL_SERVERS_DIR/Calendar-Autoauth-MCP-Server" "$LOCAL_SERVERS_DIR/Calendar-Autoauth-MCP-Server/build/index.js" || {
  record_package_result "google_calendar" "failed" 180 "$LOCAL_SERVERS_DIR/Calendar-Autoauth-MCP-Server/build/index.js" "false" "build_error"
  exit 1
}
ensure_file "$LOCAL_SERVERS_DIR/Calendar-Autoauth-MCP-Server/build/index.js" "google_calendar" || exit 1

maybe_build_node_package "canvas" 900 "$LOCAL_SERVERS_DIR/mcp-canvas-lms" "$LOCAL_SERVERS_DIR/mcp-canvas-lms/build/index.js" || {
  record_package_result "canvas" "failed" 900 "$LOCAL_SERVERS_DIR/mcp-canvas-lms/build/index.js" "false" "timeout_or_build_error"
  exit 1
}
ensure_file "$LOCAL_SERVERS_DIR/mcp-canvas-lms/build/index.js" "canvas" || exit 1

maybe_build_node_package "howtocook" 300 "$LOCAL_SERVERS_DIR/HowToCook-mcp" "$LOCAL_SERVERS_DIR/HowToCook-mcp/build/index.js" || {
  record_package_result "howtocook" "failed" 300 "$LOCAL_SERVERS_DIR/HowToCook-mcp/build/index.js" "false" "build_error"
  exit 1
}
ensure_file "$LOCAL_SERVERS_DIR/HowToCook-mcp/build/index.js" "howtocook" || exit 1

maybe_build_node_package "memory" 300 "$LOCAL_SERVERS_DIR/servers/src/memory" "$LOCAL_SERVERS_DIR/servers/src/memory/dist/index.js" || {
  record_package_result "memory" "failed" 300 "$LOCAL_SERVERS_DIR/servers/src/memory/dist/index.js" "false" "build_error"
  exit 1
}
ensure_file "$LOCAL_SERVERS_DIR/servers/src/memory/dist/index.js" "memory" || exit 1

maybe_build_node_package "google_forms" 300 "$LOCAL_SERVERS_DIR/google-forms-mcp" "$LOCAL_SERVERS_DIR/google-forms-mcp/build/index.js" || {
  record_package_result "google_forms" "failed" 300 "$LOCAL_SERVERS_DIR/google-forms-mcp/build/index.js" "false" "build_error"
  exit 1
}
ensure_file "$LOCAL_SERVERS_DIR/google-forms-mcp/build/index.js" "google_forms" || exit 1

maybe_build_node_package "fetch" 300 "$LOCAL_SERVERS_DIR/mcp-npx-fetch" "$LOCAL_SERVERS_DIR/mcp-npx-fetch/dist/index.js" || {
  record_package_result "fetch" "failed" 300 "$LOCAL_SERVERS_DIR/mcp-npx-fetch/dist/index.js" "false" "build_error"
  exit 1
}
ensure_file "$LOCAL_SERVERS_DIR/mcp-npx-fetch/dist/index.js" "fetch" || exit 1

maybe_build_node_package "notion" 900 "$LOCAL_SERVERS_DIR/notion-mcp-server" "$LOCAL_SERVERS_DIR/notion-mcp-server/bin/cli.mjs" || {
  record_package_result "notion" "failed" 900 "$LOCAL_SERVERS_DIR/notion-mcp-server/bin/cli.mjs" "false" "timeout_or_build_error"
  exit 1
}
ensure_file "$LOCAL_SERVERS_DIR/notion-mcp-server/bin/cli.mjs" "notion" || exit 1

maybe_build_node_package "woocommerce" 300 "$LOCAL_SERVERS_DIR/woocommerce-mcp" "$LOCAL_SERVERS_DIR/woocommerce-mcp/dist/index.js" || {
  record_package_result "woocommerce" "failed" 300 "$LOCAL_SERVERS_DIR/woocommerce-mcp/dist/index.js" "false" "build_error"
  exit 1
}
ensure_file "$LOCAL_SERVERS_DIR/woocommerce-mcp/dist/index.js" "woocommerce" || exit 1

maybe_build_node_package "youtube" 600 "$LOCAL_SERVERS_DIR/youtube-mcp-server" "$LOCAL_SERVERS_DIR/youtube-mcp-server/dist/index.js" || {
  record_package_result "youtube" "failed" 600 "$LOCAL_SERVERS_DIR/youtube-mcp-server/dist/index.js" "false" "build_error"
  exit 1
}
ensure_file "$LOCAL_SERVERS_DIR/youtube-mcp-server/dist/index.js" "youtube" || exit 1

maybe_build_python_package "youtube_transcript" 900 "$LOCAL_SERVERS_DIR/mcp-youtube-transcript" "$LOCAL_SERVERS_DIR/mcp-youtube-transcript/.venv/bin/python3" || {
  record_package_result "youtube_transcript" "failed" 900 "$LOCAL_SERVERS_DIR/mcp-youtube-transcript/.venv/bin/python3" "false" "timeout_or_build_error"
  exit 1
}
ensure_file "$LOCAL_SERVERS_DIR/mcp-youtube-transcript/.venv/bin/python3" "youtube_transcript" || exit 1

cd "$ROOT_DIR"
python scripts/preflight_mcp_paths.py --json-output ../.validation_logs/toolathlon_preflight_summary.json

echo "✓ Required MCP artifacts built successfully."
echo "Build summary: $BUILD_SUMMARY_FILE"
