#!/usr/bin/env bash
set -euo pipefail

export TOOLATHLON_PROFILE=full
export RUN_INTEGRATION="${RUN_INTEGRATION:-1}"
export RUN_DOCKER="${RUN_DOCKER:-1}"
export ENFORCE_RC_SMOKE_PROFILE=0
bash "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/validate_workspace.sh"
