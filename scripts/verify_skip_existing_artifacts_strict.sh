#!/usr/bin/env bash
# shellcheck shell=bash disable=SC2250,SC2292
# trunk-ignore-all(shellcheck)
# Verify strict SKIP_EXISTING_ARTIFACTS behavior for smoke-profile Toolathlon builds.
#
# This check enforces two guarantees:
# 1) Healthy runtime readiness allows skip (reason=runtime_ready_skip).
# 2) Incomplete runtime readiness forces rebuild (reason=rebuilt_after_npm_tree_unhealthy).

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
TOOLATHLON_DIR="$REPO_ROOT/toolathlon-gym-curated"
SUMMARY_PATH="$REPO_ROOT/.validation_logs/toolathlon_artifact_build_summary.json"
PYTHON_PROFILE_DIR="$TOOLATHLON_DIR/profiles/skip_python"
PYTHON_PROFILE_JSON="$PYTHON_PROFILE_DIR/mcp_servers.json"
SMOKE_WRAPPER_DIR=""

if ! command -v python3 >/dev/null 2>&1; then
  echo "Error: python3 is required." >&2
  exit 1
fi

if [ ! -d "$TOOLATHLON_DIR" ]; then
  echo "Error: missing Toolathlon directory: $TOOLATHLON_DIR" >&2
  exit 1
fi

restore_path=""
backup_path=""
python_restore_path=""
python_backup_path=""

restore_dependency() {
  if [ -n "$backup_path" ] && [ -n "$restore_path" ] && [ -e "$backup_path" ] && [ ! -e "$restore_path" ]; then
    mv "$backup_path" "$restore_path"
  fi

  if [ -n "$python_backup_path" ] && [ -n "$python_restore_path" ] && [ -e "$python_backup_path" ] && [ ! -e "$python_restore_path" ]; then
    mv "$python_backup_path" "$python_restore_path"
  fi

  if [ -d "$PYTHON_PROFILE_DIR" ]; then
    rm -rf "$PYTHON_PROFILE_DIR"
  fi

  if [ -n "$SMOKE_WRAPPER_DIR" ] && [ -d "$SMOKE_WRAPPER_DIR" ]; then
    rm -rf "$SMOKE_WRAPPER_DIR"
  fi
}

trap restore_dependency EXIT

read_reason_for_package() {
  local package_name="$1"

  python3 - "$SUMMARY_PATH" "$package_name" <<'PYEOF'
import json
import sys

summary_path = sys.argv[1]
package_name = sys.argv[2]

with open(summary_path, "r", encoding="utf-8") as f:
    data = json.load(f)

for item in data.get("packages", []):
    if item.get("package") == package_name:
        print(item.get("reason", ""))
        raise SystemExit(0)

raise SystemExit(1)
PYEOF
}

assert_summary_sane() {
  local expected_profile="${1:-smoke}"
  local expected_count="${2:-3}"

  python3 - "$SUMMARY_PATH" "$expected_profile" "$expected_count" <<'PYEOF'
import json
import sys

expected_profile = sys.argv[2]
expected_count = int(sys.argv[3])

summary_path = sys.argv[1]

with open(summary_path, "r", encoding="utf-8") as f:
    data = json.load(f)

if data.get("profile") != expected_profile:
    raise SystemExit(f"Expected profile={expected_profile}, got {data.get('profile')!r}")
if data.get("overall_status") != "passed":
    raise SystemExit(f"Expected overall_status=passed, got {data.get('overall_status')!r}")
if data.get("expected_package_count") != expected_count:
    raise SystemExit(f"Expected expected_package_count={expected_count}, got {data.get('expected_package_count')!r}")
if data.get("package_count") != expected_count:
    raise SystemExit(f"Expected package_count={expected_count}, got {data.get('package_count')!r}")
if data.get("failed_count") != 0:
    raise SystemExit(f"Expected failed_count=0, got {data.get('failed_count')!r}")
PYEOF
}

run_build() {
  local profile="$1"
  local force_rebuild="$2"
  local skip_existing="$3"
  local skip_timeout="${4:-120}"

  (
    cd "$TOOLATHLON_DIR"
    TOOLATHLON_PROFILE="$profile" \
    FORCE_REBUILD="$force_rebuild" \
    SKIP_EXISTING_ARTIFACTS="$skip_existing" \
    SKIP_SMOKE_TIMEOUT_SECONDS="$skip_timeout" \
    bash scripts/build_required_mcp_artifacts.sh
  )
}

assert_reason_equals() {
  local package_name="$1"
  local expected="$2"

  local actual
  actual="$(read_reason_for_package "$package_name")"
  if [ "$actual" != "$expected" ]; then
    echo "Expected $package_name reason=$expected, got: $actual" >&2
    exit 1
  fi
}

assert_skipped_existing_equals() {
  local package_name="$1"
  local expected="$2"

  local actual
  actual="$(python3 - "$SUMMARY_PATH" "$package_name" <<'PYEOF'
import json
import sys

summary_path = sys.argv[1]
package_name = sys.argv[2]

with open(summary_path, "r", encoding="utf-8") as f:
    data = json.load(f)

for package in data.get("packages", []):
    if package.get("package") == package_name:
        value = package.get("skipped_existing")
        if value is True:
            print("true")
        elif value is False:
            print("false")
        else:
            print("")
        raise SystemExit(0)

print("")
PYEOF
)"

  if [ "$actual" != "$expected" ]; then
    echo "Expected $package_name skipped_existing=$expected, got: $actual" >&2
    exit 1
  fi
}

create_python_test_profile() {
  mkdir -p "$PYTHON_PROFILE_DIR"
  cat > "$PYTHON_PROFILE_JSON" <<'EOF'
{
  "servers": [
    "youtube_transcript"
  ]
}
EOF
}

run_build_with_target_smoke_failure() {
  local real_python
  real_python="$(command -v python3)"
  if [ -z "$real_python" ]; then
    echo "python3 is required for runtime smoke perturbation" >&2
    exit 1
  fi

  SMOKE_WRAPPER_DIR="$(mktemp -d "${TMPDIR:-/tmp}/skipcheck-smoke-wrapper.XXXXXX")"
  cat > "$SMOKE_WRAPPER_DIR/python3" <<EOF
#!/usr/bin/env bash
if [ "\$#" -gt 0 ] && [ "\$1" = "scripts/smoke_mcp_servers.py" ]; then
  shift
  for arg in "\$@"; do
    if [ "\$arg" = "--target" ]; then
      exit 1
    fi
  done
  exec "$real_python" scripts/smoke_mcp_servers.py "\$@"
fi
exec "$real_python" "\$@"
EOF
  chmod +x "$SMOKE_WRAPPER_DIR/python3"

  (
    cd "$TOOLATHLON_DIR"
    PATH="$SMOKE_WRAPPER_DIR:$PATH" \
    TOOLATHLON_PROFILE="smoke" \
    FORCE_REBUILD="0" \
    SKIP_EXISTING_ARTIFACTS="1" \
    SKIP_SMOKE_TIMEOUT_SECONDS="120" \
    bash scripts/build_required_mcp_artifacts.sh
  )

  rm -rf "$SMOKE_WRAPPER_DIR"
  SMOKE_WRAPPER_DIR=""
}

echo "== test_skip_accepts_fully_ready_node_target: baseline rebuild =="
run_build "smoke" 1 0

assert_summary_sane

echo "== test_skip_accepts_fully_ready_node_target: healthy runtime should skip =="
run_build "smoke" 0 1

assert_summary_sane

for pkg in rail_12306 filesystem; do
  assert_reason_equals "$pkg" "runtime_ready_skip"
done

echo "== test_skip_rejects_missing_node_modules =="
restore_path="$TOOLATHLON_DIR/local_servers/filesystem/node_modules"
if [ ! -d "$restore_path" ]; then
  echo "Error: expected node_modules missing before perturbation: $restore_path" >&2
  exit 1
fi

backup_path="$(mktemp -d "${TMPDIR:-/tmp}/skipcheck-node-modules-root.XXXXXX")/node_modules"
mv "$restore_path" "$backup_path"

run_build "smoke" 0 1

if [ -d "$restore_path" ]; then
  rm -rf "$backup_path"
  backup_path=""
  restore_path=""
fi

assert_summary_sane
assert_reason_equals "filesystem" "rebuilt_after_node_modules_missing"

echo "== test_skip_rejects_failed_npm_tree =="
restore_path="$TOOLATHLON_DIR/local_servers/filesystem/node_modules/@modelcontextprotocol/sdk"
if [ ! -d "$restore_path" ]; then
  echo "Error: expected dependency path missing before perturbation: $restore_path" >&2
  exit 1
fi

backup_path="$(mktemp -d "${TMPDIR:-/tmp}/skipcheck-node-modules.XXXXXX")/sdk"
mv "$restore_path" "$backup_path"

run_build "smoke" 0 1

# Build should recreate dependencies; clear restore pointers only if recreated.
if [ -d "$restore_path" ]; then
  rm -rf "$backup_path"
  backup_path=""
  restore_path=""
fi

assert_summary_sane

assert_reason_equals "filesystem" "rebuilt_after_npm_tree_unhealthy"

echo "== test_skip_rejects_missing_artifact =="
restore_path="$TOOLATHLON_DIR/local_servers/filesystem/dist/index.js"
if [ ! -f "$restore_path" ]; then
  echo "Error: expected artifact missing before perturbation: $restore_path" >&2
  exit 1
fi

backup_path="$(mktemp -d "${TMPDIR:-/tmp}/skipcheck-artifact.XXXXXX")/index.js"
mv "$restore_path" "$backup_path"

run_build "smoke" 0 1

if [ -f "$restore_path" ]; then
  rm -f "$backup_path"
  backup_path=""
  restore_path=""
fi

assert_summary_sane
assert_skipped_existing_equals "filesystem" "false"

echo "== test_skip_rejects_runtime_smoke_failure =="
run_build_with_target_smoke_failure

assert_summary_sane
assert_reason_equals "filesystem" "rebuilt_after_runtime_smoke_failed"

echo "== test_python_skip_rejects_missing_venv_python =="
create_python_test_profile
run_build "skip_python" 1 0

assert_summary_sane "skip_python" 1

echo "== test_python_skip_accepts_fully_ready_target =="
run_build "skip_python" 0 1

assert_summary_sane "skip_python" 1
assert_reason_equals "youtube_transcript" "runtime_ready_skip"
assert_skipped_existing_equals "youtube_transcript" "true"

python_restore_path="$TOOLATHLON_DIR/local_servers/mcp-youtube-transcript/.venv/bin/python3"
if [ ! -x "$python_restore_path" ]; then
  echo "Error: expected python3 executable missing before perturbation: $python_restore_path" >&2
  exit 1
fi

python_backup_path="$(mktemp -d "${TMPDIR:-/tmp}/skipcheck-python-missing.XXXXXX")/python3"
mv "$python_restore_path" "$python_backup_path"

run_build "skip_python" 0 1

if [ -x "$python_restore_path" ]; then
  rm -f "$python_backup_path"
  python_backup_path=""
  python_restore_path=""
fi

assert_summary_sane "skip_python" 1
assert_skipped_existing_equals "youtube_transcript" "false"

echo "== test_python_skip_rejects_artifact_smoke_failure =="
python_restore_path="$TOOLATHLON_DIR/mcp_youtube_transcript.py"
if [ -e "$python_restore_path" ]; then
  echo "Error: expected temporary shadow module path to be absent before perturbation: $python_restore_path" >&2
  exit 1
fi

python_backup_path=""
cat > "$python_restore_path" <<'EOF'
raise RuntimeError("skipcheck import failure")
EOF

run_build "skip_python" 0 1

rm -f "$python_restore_path"
python_restore_path=""

assert_summary_sane "skip_python" 1
assert_reason_equals "youtube_transcript" "rebuilt_after_python_runtime_unhealthy"

echo "Skip strictness verification passed."
