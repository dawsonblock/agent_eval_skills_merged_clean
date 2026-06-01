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

Environment:
  RELEASE_ZIP_PATH   Default --release path when no CLI value is provided
  EVIDENCE_ZIP_PATH  Default --evidence path when no CLI value is provided
USAGE
}

RELEASE_PATH="${RELEASE_ZIP_PATH:-}"
EVIDENCE_PATH="${EVIDENCE_ZIP_PATH:-}"

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

cd "$REPO_ROOT"
verify_args=(--lock "$LOCK_PATH")
if [ -n "$RELEASE_PATH" ]; then
  verify_args+=(--release "$RELEASE_PATH")
fi
if [ -n "$EVIDENCE_PATH" ]; then
  verify_args+=(--evidence "$EVIDENCE_PATH")
fi

python3 scripts/verify_release_pair.py "${verify_args[@]}"
