#!/usr/bin/env bash
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

restore_dependency() {
  if [ -n "$backup_path" ] && [ -n "$restore_path" ] && [ -d "$backup_path" ] && [ ! -e "$restore_path" ]; then
    mv "$backup_path" "$restore_path"
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
  python3 - "$SUMMARY_PATH" <<'PYEOF'
import json
import sys

summary_path = sys.argv[1]

with open(summary_path, "r", encoding="utf-8") as f:
    data = json.load(f)

if data.get("profile") != "smoke":
    raise SystemExit("Expected profile=smoke")
if data.get("overall_status") != "passed":
    raise SystemExit(f"Expected overall_status=passed, got {data.get('overall_status')!r}")
if data.get("expected_package_count") != 3:
    raise SystemExit(f"Expected expected_package_count=3, got {data.get('expected_package_count')!r}")
if data.get("package_count") != 3:
    raise SystemExit(f"Expected package_count=3, got {data.get('package_count')!r}")
if data.get("failed_count") != 0:
    raise SystemExit(f"Expected failed_count=0, got {data.get('failed_count')!r}")
PYEOF
}

echo "== Skip strictness check: baseline rebuild =="
(
  cd "$TOOLATHLON_DIR"
  TOOLATHLON_PROFILE=smoke FORCE_REBUILD=1 bash scripts/build_required_mcp_artifacts.sh
)

assert_summary_sane

echo "== Skip strictness check: healthy runtime should skip =="
(
  cd "$TOOLATHLON_DIR"
  TOOLATHLON_PROFILE=smoke SKIP_EXISTING_ARTIFACTS=1 bash scripts/build_required_mcp_artifacts.sh
)

assert_summary_sane

for pkg in rail_12306 filesystem google_calendar; do
  reason="$(read_reason_for_package "$pkg")"
  if [ "$reason" != "runtime_ready_skip" ]; then
    echo "Expected $pkg to skip with reason=runtime_ready_skip, got: $reason" >&2
    exit 1
  fi
done

echo "== Skip strictness check: unhealthy node dependency should force rebuild =="
restore_path="$TOOLATHLON_DIR/local_servers/filesystem/node_modules/@modelcontextprotocol/sdk"
if [ ! -d "$restore_path" ]; then
  echo "Error: expected dependency path missing before perturbation: $restore_path" >&2
  exit 1
fi

backup_path="${restore_path}.skipcheck-backup-$$"
mv "$restore_path" "$backup_path"

(
  cd "$TOOLATHLON_DIR"
  TOOLATHLON_PROFILE=smoke SKIP_EXISTING_ARTIFACTS=1 bash scripts/build_required_mcp_artifacts.sh
)

# Build should recreate dependencies; clear restore pointers only if recreated.
if [ -d "$restore_path" ]; then
  rm -rf "$backup_path"
  backup_path=""
  restore_path=""
fi

assert_summary_sane

filesystem_reason="$(read_reason_for_package "filesystem")"
if [ "$filesystem_reason" != "rebuilt_after_npm_tree_unhealthy" ]; then
  echo "Expected filesystem rebuild reason rebuilt_after_npm_tree_unhealthy, got: $filesystem_reason" >&2
  exit 1
fi

echo "Skip strictness verification passed."
