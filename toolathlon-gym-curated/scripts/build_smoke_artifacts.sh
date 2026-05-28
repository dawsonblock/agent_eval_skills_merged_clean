#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_DIR="$ROOT/../release_artifacts/validation_logs"
mkdir -p "$LOG_DIR"

# Bash 3 compatibility: use explicit per-server variables (macOS /bin/bash).
_BSTATUS_rail_12306="pass"
_BSTATUS_filesystem="pass"
_BHAS_BUILD_rail_12306="false"
_BHAS_BUILD_filesystem="false"

set_server_result() {
  local name="$1"
  local status="$2"
  local has_build="$3"
  case "$name" in
    rail_12306)
      _BSTATUS_rail_12306="$status"
      _BHAS_BUILD_rail_12306="$has_build"
      ;;
    filesystem)
      _BSTATUS_filesystem="$status"
      _BHAS_BUILD_filesystem="$has_build"
      ;;
    *)
      echo "FAIL: unknown smoke server mapping: $name"
      exit 1
      ;;
  esac
}

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
    set_server_result "$name" "fail" "false"
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
    set_server_result "$name" "fail" "false"
    cd "$ROOT"
    return 1
  fi

  if [ "$install_ok" = "false" ]; then
    set_server_result "$name" "fail" "false"
    cd "$ROOT"
    return 1
  fi

  local has_build="false"
  if npm run | grep -q " build"; then
    has_build="true"
    npm run build || { set_server_result "$name" "fail" "true"; cd "$ROOT"; return 1; }
  fi
  set_server_result "$name" "pass" "$has_build"
  cd "$ROOT"
}

build_server "rail_12306"
build_server "filesystem"
echo "PASS: smoke artifacts built"

# Export status for the Python JSON writer.
export _BSTATUS_rail_12306
export _BSTATUS_filesystem
export _BHAS_BUILD_rail_12306
export _BHAS_BUILD_filesystem
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