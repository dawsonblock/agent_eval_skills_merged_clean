#!/usr/bin/env bash
set -euo pipefail

export TOOLATHLON_PROFILE=full
export RUN_INTEGRATION="${RUN_INTEGRATION:-1}"
export RUN_DOCKER="${RUN_DOCKER:-1}"
bash "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/validate_workspace.sh"
