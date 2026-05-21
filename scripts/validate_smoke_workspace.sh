#!/usr/bin/env bash
set -euo pipefail

export TOOLATHLON_PROFILE=smoke
bash "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/validate_workspace.sh"
