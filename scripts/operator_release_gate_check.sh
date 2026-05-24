#!/usr/bin/env bash
# Operator helper: run canonical pair verification and print required check names.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

usage() {
  cat <<'USAGE'
Usage: bash scripts/operator_release_gate_check.sh [--release PATH] [--evidence PATH] [--no-verify]

Runs canonical release/evidence verification and prints required GitHub check names
for branch protection/ruleset setup.

Options:
  --release PATH   Path to release ZIP (passed through to verify_release_pair.sh)
  --evidence PATH  Path to evidence ZIP (passed through to verify_release_pair.sh)
  --no-verify      Skip ZIP verification and print check names only
  -h, --help       Show this help
USAGE
}

verify_release=1
release_path=""
evidence_path=""

while [ "$#" -gt 0 ]; do
  case "$1" in
    --release)
      if [ "$#" -lt 2 ]; then
        echo "Missing value for --release" >&2
        exit 1
      fi
      release_path="$2"
      shift 2
      ;;
    --evidence)
      if [ "$#" -lt 2 ]; then
        echo "Missing value for --evidence" >&2
        exit 1
      fi
      evidence_path="$2"
      shift 2
      ;;
    --no-verify)
      verify_release=0
      shift
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

if [ "$verify_release" -eq 1 ]; then
  verify_args=()
  if [ -n "$release_path" ]; then
    verify_args+=(--release "$release_path")
  fi
  if [ -n "$evidence_path" ]; then
    verify_args+=(--evidence "$evidence_path")
  fi

  echo "Running canonical pair verification..."
  if [ "${#verify_args[@]}" -gt 0 ]; then
    (cd "$REPO_ROOT" && bash scripts/verify_release_pair.sh "${verify_args[@]}")
  else
    (cd "$REPO_ROOT" && bash scripts/verify_release_pair.sh)
  fi
  echo
fi

cat <<'CHECKS'
Required check names for repository rules:
1. Validate Workspace / Unified Workspace Validation
2. Validate Workspace / Verify Canonical Attested Pair
3. Validate Workspace / Classify Uploaded Release Artifact

Manual pre-publish gate:
1. Release Attested Pair Gate / Verify Canonical Attested Pair
CHECKS
