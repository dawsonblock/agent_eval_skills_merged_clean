#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
LOCK_PATH="${LOCK_PATH:-$REPO_ROOT/release_artifacts/release_lock.json}"

usage() {
  cat <<'USAGE'
Usage: bash scripts/classify_release_upload.sh --release PATH [--evidence PATH] [--json-output PATH] [--lock PATH]

This wrapper delegates to scripts/classify_release_artifact.py.
USAGE
}

RELEASE_PATH=""
EVIDENCE_PATH=""
JSON_OUTPUT_PATH=""

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
    --json-output)
      JSON_OUTPUT_PATH="$2"
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
  echo "Error: --release is required" >&2
  usage >&2
  exit 1
fi

cmd=(python3 scripts/classify_release_artifact.py "$RELEASE_PATH" --lock "$LOCK_PATH")
if [ -n "$EVIDENCE_PATH" ]; then
  cmd+=(--evidence "$EVIDENCE_PATH")
fi
if [ -n "$JSON_OUTPUT_PATH" ]; then
  cmd+=(--json-out "$JSON_OUTPUT_PATH")
fi

cd "$REPO_ROOT"
"${cmd[@]}"
