#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
PARENT_DIR="$(dirname "$ROOT_DIR")"
OUT_DEFAULT="$PARENT_DIR/agent_eval_skills_merged_clean-pruned-smoke.zip"

OUT="${OUT:-$OUT_DEFAULT}"

if [ "$#" -gt 0 ]; then
  OUT="$1"
fi

RELEASE_ZIP_OUTPUT="$OUT" bash "$SCRIPT_DIR/create_release_zip.sh"

echo "Created: $OUT"