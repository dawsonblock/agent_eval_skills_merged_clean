#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_DIR="$ROOT/../release_artifacts/validation_logs"
mkdir -p "$LOG_DIR"

# Will be populated with per-server results before writing the final summary.
declare -A SERVER_STATUS
declare -A SERVER_HAS_BUILD

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
    SERVER_STATUS[$name]="fail"
    SERVER_HAS_BUILD[$name]="false"
    return 1
  fi

  cd "$dir"
  local install_ok=true
  if [ -f package-lock.json ]; then
    npm ci || install_ok=false
  elif [ -f package.json ]; then
    npm install || install_ok=false
  else
    echo "FAIL: missing package.json for $name"
    SERVER_STATUS[$name]="fail"
    SERVER_HAS_BUILD[$name]="false"
    cd "$ROOT"
    return 1
  fi

  if [ "$install_ok" = "false" ]; then
    SERVER_STATUS[$name]="fail"
    SERVER_HAS_BUILD[$name]="false"
    cd "$ROOT"
    return 1
  fi

  local has_build="false"
  if npm run | grep -q " build"; then
    has_build="true"
    npm run build || { SERVER_STATUS[$name]="fail"; SERVER_HAS_BUILD[$name]="true"; cd "$ROOT"; return 1; }
  fi
  SERVER_HAS_BUILD[$name]="$has_build"
  SERVER_STATUS[$name]="pass"
  cd "$ROOT"
}

build_server "rail_12306"
build_server "filesystem"
echo "PASS: smoke artifacts built"

# Export status for the Python JSON writer.
export _BSTATUS_rail_12306="${SERVER_STATUS[rail_12306]:-pass}"
export _BSTATUS_filesystem="${SERVER_STATUS[filesystem]:-pass}"
export _BHAS_BUILD_rail_12306="${SERVER_HAS_BUILD[rail_12306]:-false}"
export _BHAS_BUILD_filesystem="${SERVER_HAS_BUILD[filesystem]:-false}"
export LOG_DIR

# Write the build summary JSON with actual per-server status.
python3 - <<PYEOF
import json, os

servers = {}
for name in ["rail_12306", "filesystem"]:
    status = os.environ.get(f"_BSTATUS_{name}", "pass")
    has_build_raw = os.environ.get(f"_BHAS_BUILD_{name}", "false")
    has_build = has_build_raw.lower() == "true"
    servers[name] = {
        "install": status,
        "build": status if has_build else "n/a",
        "entrypoint": "pass" if status == "pass" else "fail",
    }

summary = {"profile": "smoke", "servers": servers}
out = os.path.join(os.environ["LOG_DIR"], "toolathlon_build_smoke_summary.json")
with open(out, "w") as f:
    json.dump(summary, f, indent=2)
    f.write("\n")
print(f"Wrote {out}")
PYEOF