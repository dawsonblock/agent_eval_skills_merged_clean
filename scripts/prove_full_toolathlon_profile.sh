#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$ROOT"

export TOOLATHLON_PROFILE=full
export ENFORCE_RC_SMOKE_PROFILE=0

bash scripts/validate_workspace.sh

mkdir -p .validation_logs/full_profile
cp .validation_logs/validation_summary.json .validation_logs/full_profile/validation_summary.json

echo "Full Toolathlon profile validation completed."
