#!/usr/bin/env bash
set -euo pipefail

export TOOLATHLON_PROFILE=smoke
export ENFORCE_RC_SMOKE_PROFILE=1
bash "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/validate_workspace.sh"
