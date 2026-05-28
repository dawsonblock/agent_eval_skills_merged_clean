#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
LOCK_PATH="${LOCK_PATH:-$REPO_ROOT/release_artifacts/release_lock.json}"

usage() {
  cat <<'USAGE'
Usage: bash scripts/verify_release_pair.sh [--release PATH] [--evidence PATH] [--lock PATH]

Defaults:
  --lock     release_artifacts/release_lock.json
  --release  value from release_lock.json.release_zip
  --evidence value from release_lock.json.evidence_zip
USAGE
}

RELEASE_PATH=""
EVIDENCE_PATH=""

while [ "$#" -gt 0 ]; do
  case "$1" in
    --release)
      RELEASE_PATH="$2"
      shift 2
      ;;
    --evidence)
      EVIDENCE_PATH="$2"
      shift 2
      ;;
    --lock)
      LOCK_PATH="$2"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage >&2
      exit 1
      ;;
  esac
done

if [ -z "$RELEASE_PATH" ]; then
  RELEASE_PATH="$(python3 - "$LOCK_PATH" <<'PY'
import json
import sys
from pathlib import Path
p = Path(sys.argv[1])
lock = json.loads(p.read_text(encoding='utf-8'))
print(lock['release_zip'])
PY
)"
fi

if [ -z "$EVIDENCE_PATH" ]; then
  EVIDENCE_PATH="$(python3 - "$LOCK_PATH" <<'PY'
import json
import sys
from pathlib import Path
p = Path(sys.argv[1])
lock = json.loads(p.read_text(encoding='utf-8'))
print(lock['evidence_zip'])
PY
)"
fi

cd "$REPO_ROOT"
python3 scripts/verify_release_pair.py \
  --release "$RELEASE_PATH" \
  --evidence "$EVIDENCE_PATH" \
  --lock "$LOCK_PATH"
