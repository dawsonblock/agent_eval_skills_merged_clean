#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
REPO_ROOT="$(cd "$ROOT_DIR/.." && pwd)"

mkdir -p "$REPO_ROOT/release_artifacts/validation_logs"

echo "Profile: smoke"
echo "Node: $(node --version)"
echo "npm: $(npm --version)"

TOOLATHLON_PROFILE=smoke bash "$ROOT_DIR/scripts/build_required_mcp_artifacts.sh"

if [ -f "$REPO_ROOT/.validation_logs/toolathlon_artifact_build_summary.json" ]; then
  cp \
    "$REPO_ROOT/.validation_logs/toolathlon_artifact_build_summary.json" \
    "$REPO_ROOT/release_artifacts/validation_logs/toolathlon_build_smoke_summary.json"
fi

echo "Wrote release_artifacts/validation_logs/toolathlon_build_smoke_summary.json"