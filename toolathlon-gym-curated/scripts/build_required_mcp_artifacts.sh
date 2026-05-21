#!/usr/bin/env bash
# Build the minimal set of MCP server artifacts required by preflight.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && cd .. && pwd)"
LOCAL_SERVERS_DIR="${LOCAL_SERVERS_PATH:-$ROOT_DIR/local_servers}"
SKIP_EXISTING_ARTIFACTS="${SKIP_EXISTING_ARTIFACTS:-0}"
FORCE_REBUILD="${FORCE_REBUILD:-0}"
BUILD_SUMMARY_FILE="${ROOT_DIR}/../.validation_logs/toolathlon_artifact_build_summary.json"
EXPECTED_PACKAGE_COUNT=12

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

  # Accept only regular files or symlinks; directories must not satisfy artifact checks.
  if [ ! -e "$file_path" ] || { [ ! -f "$file_path" ] && [ ! -L "$file_path" ]; }; then
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
  [ -e "$path" ] && { [ -f "$path" ] || [ -L "$path" ]; }
}

# Initialize JSON output
init_build_summary() {
  mkdir -p "$(dirname "$BUILD_SUMMARY_FILE")"
  cat >"$BUILD_SUMMARY_FILE" <<EOF
{
  "overall_status": "in_progress",
  "expected_package_count": ${EXPECTED_PACKAGE_COUNT},
  "package_count": 0,
  "passed_count": 0,
  "failed_count": 0,
  "packages": []
}
EOF
}

mark_build_failed_if_in_progress() {
  local reason="${1:-build_interrupted}"

  if [ ! -f "$BUILD_SUMMARY_FILE" ]; then
    return 0
  fi

  python3 - "$BUILD_SUMMARY_FILE" "$reason" <<'PYEOF'
import json
import sys

summary_file = sys.argv[1]
reason = sys.argv[2]

with open(summary_file, 'r', encoding='utf-8') as f:
    data = json.load(f)

if data.get('overall_status') != 'passed':
    data['overall_status'] = 'failed'
    if not data.get('reason'):
        data['reason'] = reason

with open(summary_file, 'w', encoding='utf-8') as f:
    json.dump(data, f, indent=2)
PYEOF
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

with open(summary_file, 'w') as f:
    json.dump(data, f, indent=2)
PYEOF
}

finalize_build_summary() {
  local preflight_json="$1"
  shift

  python3 - "$BUILD_SUMMARY_FILE" "$preflight_json" "$@" <<'PYEOF'
import json
import sys
from pathlib import Path

summary_path = Path(sys.argv[1])
preflight_path = Path(sys.argv[2])
required_artifacts = [Path(p) for p in sys.argv[3:]]

with summary_path.open('r', encoding='utf-8') as f:
  data = json.load(f)

expected = int(data.get('expected_package_count', 0))
package_count = int(data.get('package_count', 0))
failed_count = int(data.get('failed_count', 0))

reasons = []

if failed_count != 0:
  reasons.append(f"failed_count={failed_count}")

if package_count != expected:
  reasons.append(f"incomplete_build: expected {expected}, got {package_count}")

missing_artifacts = [str(p) for p in required_artifacts if not (p.exists() and (p.is_file() or p.is_symlink()))]
if missing_artifacts:
  reasons.append(f"artifact_missing: {', '.join(missing_artifacts)}")

preflight_missing = None
if preflight_path.exists():
  try:
    with preflight_path.open('r', encoding='utf-8') as f:
      preflight = json.load(f)
    preflight_missing = int(preflight.get('missing_count', -1))
  except Exception as exc:
    reasons.append(f"preflight_parse_error: {exc}")
else:
  reasons.append("preflight_summary_missing")

if preflight_missing is not None and preflight_missing != 0:
  reasons.append(f"preflight_missing_count={preflight_missing}")

if reasons:
  data['overall_status'] = 'failed'
  data['reason'] = '; '.join(reasons)
else:
  data['overall_status'] = 'passed'
  data.pop('reason', None)

with summary_path.open('w', encoding='utf-8') as f:
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
  CURRENT_PACKAGE_START_EPOCH="$start"

  if [ "${FORCE_REBUILD:-0}" = "1" ]; then
    echo "→ Force rebuild requested for $name"
    build_with_timeout "$name" "$timeout_sec" build_node_package "$pkg_dir" "$name" || return 1
  elif [ "${SKIP_EXISTING_ARTIFACTS:-0}" = "1" ] && artifact_exists "$artifact"; then
    echo "✓ $name artifact already exists: $artifact (skipped)"
    ensure_file "$artifact" "$name" || return 1
    local elapsed
    elapsed="$(( $(date +%s) - start ))"
    record_package_result "$name" "passed" "$elapsed" "$artifact" "true"
    return 0
  else
    build_with_timeout "$name" "$timeout_sec" build_node_package "$pkg_dir" "$name" || return 1
  fi

  ensure_file "$artifact" "$name" || return 1
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
  CURRENT_PACKAGE_START_EPOCH="$start"

  if [ "${FORCE_REBUILD:-0}" = "1" ]; then
    echo "→ Force rebuild requested for $name"
    build_with_timeout "$name" "$timeout_sec" build_python_uv_package "$pkg_dir" "$name" || return 1
  elif [ "${SKIP_EXISTING_ARTIFACTS:-0}" = "1" ] && artifact_exists "$artifact"; then
    echo "✓ $name artifact already exists: $artifact (skipped)"
    ensure_file "$artifact" "$name" || return 1
    local elapsed
    elapsed="$(( $(date +%s) - start ))"
    record_package_result "$name" "passed" "$elapsed" "$artifact" "true"
    return 0
  else
    build_with_timeout "$name" "$timeout_sec" build_python_uv_package "$pkg_dir" "$name" || return 1
  fi

  ensure_file "$artifact" "$name" || return 1
  local elapsed
  elapsed="$(( $(date +%s) - start ))"
  record_package_result "$name" "passed" "$elapsed" "$artifact"
}

fail_package() {
  local name="$1"
  local fallback_duration="$2"
  local artifact="$3"
  local reason="$4"
  local start_epoch="${5:-${CURRENT_PACKAGE_START_EPOCH:-}}"
  local duration="$fallback_duration"

  if [[ "$start_epoch" =~ ^[0-9]+$ ]]; then
    duration="$(( $(date +%s) - start_epoch ))"
  fi

  record_package_result "$name" "failed" "$duration" "$artifact" "false" "$reason"
  mark_build_failed_if_in_progress "$reason"
}

echo "Building required MCP artifacts in $LOCAL_SERVERS_DIR"

# Initialize JSON summary
init_build_summary
trap 'mark_build_failed_if_in_progress "build_error"' ERR
trap 'mark_build_failed_if_in_progress "build_interrupted"; exit 130' INT TERM

# Build each package, recording results
maybe_build_node_package "rail_12306" 300 "$LOCAL_SERVERS_DIR/12306-mcp" "$LOCAL_SERVERS_DIR/12306-mcp/build/index.js" || {
  fail_package "rail_12306" 300 "$LOCAL_SERVERS_DIR/12306-mcp/build/index.js" "build_error"
  exit 1
}

maybe_build_node_package "filesystem" 300 "$LOCAL_SERVERS_DIR/filesystem" "$LOCAL_SERVERS_DIR/filesystem/dist/index.js" || {
  fail_package "filesystem" 300 "$LOCAL_SERVERS_DIR/filesystem/dist/index.js" "build_error"
  exit 1
}

maybe_build_node_package "google_calendar" 180 "$LOCAL_SERVERS_DIR/Calendar-Autoauth-MCP-Server" "$LOCAL_SERVERS_DIR/Calendar-Autoauth-MCP-Server/build/index.js" || {
  fail_package "google_calendar" 180 "$LOCAL_SERVERS_DIR/Calendar-Autoauth-MCP-Server/build/index.js" "build_error"
  exit 1
}

maybe_build_node_package "canvas" 900 "$LOCAL_SERVERS_DIR/mcp-canvas-lms" "$LOCAL_SERVERS_DIR/mcp-canvas-lms/build/index.js" || {
  fail_package "canvas" 900 "$LOCAL_SERVERS_DIR/mcp-canvas-lms/build/index.js" "timeout_or_build_error"
  exit 1
}

maybe_build_node_package "howtocook" 300 "$LOCAL_SERVERS_DIR/HowToCook-mcp" "$LOCAL_SERVERS_DIR/HowToCook-mcp/build/index.js" || {
  fail_package "howtocook" 300 "$LOCAL_SERVERS_DIR/HowToCook-mcp/build/index.js" "build_error"
  exit 1
}

maybe_build_node_package "memory" 300 "$LOCAL_SERVERS_DIR/servers/src/memory" "$LOCAL_SERVERS_DIR/servers/src/memory/dist/index.js" || {
  fail_package "memory" 300 "$LOCAL_SERVERS_DIR/servers/src/memory/dist/index.js" "build_error"
  exit 1
}

maybe_build_node_package "google_forms" 300 "$LOCAL_SERVERS_DIR/google-forms-mcp" "$LOCAL_SERVERS_DIR/google-forms-mcp/build/index.js" || {
  fail_package "google_forms" 300 "$LOCAL_SERVERS_DIR/google-forms-mcp/build/index.js" "build_error"
  exit 1
}

maybe_build_node_package "fetch" 300 "$LOCAL_SERVERS_DIR/mcp-npx-fetch" "$LOCAL_SERVERS_DIR/mcp-npx-fetch/dist/index.js" || {
  fail_package "fetch" 300 "$LOCAL_SERVERS_DIR/mcp-npx-fetch/dist/index.js" "build_error"
  exit 1
}

maybe_build_node_package "notion" 900 "$LOCAL_SERVERS_DIR/notion-mcp-server" "$LOCAL_SERVERS_DIR/notion-mcp-server/bin/cli.mjs" || {
  fail_package "notion" 900 "$LOCAL_SERVERS_DIR/notion-mcp-server/bin/cli.mjs" "timeout_or_build_error"
  exit 1
}

maybe_build_node_package "woocommerce" 300 "$LOCAL_SERVERS_DIR/woocommerce-mcp" "$LOCAL_SERVERS_DIR/woocommerce-mcp/dist/index.js" || {
  fail_package "woocommerce" 300 "$LOCAL_SERVERS_DIR/woocommerce-mcp/dist/index.js" "build_error"
  exit 1
}

maybe_build_node_package "youtube" 600 "$LOCAL_SERVERS_DIR/youtube-mcp-server" "$LOCAL_SERVERS_DIR/youtube-mcp-server/dist/index.js" || {
  fail_package "youtube" 600 "$LOCAL_SERVERS_DIR/youtube-mcp-server/dist/index.js" "build_error"
  exit 1
}

maybe_build_python_package "youtube_transcript" 900 "$LOCAL_SERVERS_DIR/mcp-youtube-transcript" "$LOCAL_SERVERS_DIR/mcp-youtube-transcript/.venv/bin/python3" || {
  fail_package "youtube_transcript" 900 "$LOCAL_SERVERS_DIR/mcp-youtube-transcript/.venv/bin/python3" "timeout_or_build_error"
  exit 1
}

cd "$ROOT_DIR"
PREFLIGHT_SUMMARY_JSON="${ROOT_DIR}/../.validation_logs/toolathlon_preflight_summary.json"
if ! python scripts/preflight_mcp_paths.py --json-output "$PREFLIGHT_SUMMARY_JSON"; then
  mark_build_failed_if_in_progress "preflight_failed"
fi

finalize_build_summary "$PREFLIGHT_SUMMARY_JSON" \
  "$LOCAL_SERVERS_DIR/12306-mcp/build/index.js" \
  "$LOCAL_SERVERS_DIR/filesystem/dist/index.js" \
  "$LOCAL_SERVERS_DIR/Calendar-Autoauth-MCP-Server/build/index.js" \
  "$LOCAL_SERVERS_DIR/mcp-canvas-lms/build/index.js" \
  "$LOCAL_SERVERS_DIR/HowToCook-mcp/build/index.js" \
  "$LOCAL_SERVERS_DIR/servers/src/memory/dist/index.js" \
  "$LOCAL_SERVERS_DIR/google-forms-mcp/build/index.js" \
  "$LOCAL_SERVERS_DIR/mcp-npx-fetch/dist/index.js" \
  "$LOCAL_SERVERS_DIR/notion-mcp-server/bin/cli.mjs" \
  "$LOCAL_SERVERS_DIR/woocommerce-mcp/dist/index.js" \
  "$LOCAL_SERVERS_DIR/youtube-mcp-server/dist/index.js" \
  "$LOCAL_SERVERS_DIR/mcp-youtube-transcript/.venv/bin/python3"

summary_status=$(python3 - "$BUILD_SUMMARY_FILE" <<'PYEOF'
import json
import sys

with open(sys.argv[1], 'r', encoding='utf-8') as f:
    data = json.load(f)
print(data.get('overall_status', 'failed'))
PYEOF
)

if [ "$summary_status" != "passed" ]; then
  echo "✗ Required MCP artifacts build summary did not pass. See $BUILD_SUMMARY_FILE" >&2
  exit 1
fi

echo "✓ Required MCP artifacts built successfully."
echo "Build summary: $BUILD_SUMMARY_FILE"
