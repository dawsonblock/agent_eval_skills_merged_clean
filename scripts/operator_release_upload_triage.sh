#!/usr/bin/env bash
# Operator helper: classify uploaded release artifacts and print triage check name.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

usage() {
  cat <<'USAGE'
Usage: bash scripts/operator_release_upload_triage.sh --release PATH [--evidence PATH] [--json-output PATH]

Runs uploaded artifact triage classification and prints the manual check name
for release upload triage records.

Options:
  --release PATH      Path to uploaded release ZIP (required)
  --evidence PATH     Optional evidence ZIP path
  --json-output PATH  Optional JSON verdict output path
  -h, --help          Show this help
USAGE
}

release_path=""
evidence_path=""
json_output_path=""

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
    --json-output)
      if [ "$#" -lt 2 ]; then
        echo "Missing value for --json-output" >&2
        exit 1
      fi
      json_output_path="$2"
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

if [ -z "$release_path" ]; then
  echo "Error: --release is required" >&2
  usage >&2
  exit 1
fi

triage_args=(--release "$release_path")
if [ -n "$evidence_path" ]; then
  triage_args+=(--evidence "$evidence_path")
fi
if [ -n "$json_output_path" ]; then
  triage_args+=(--json-output "$json_output_path")
fi

echo "Running uploaded artifact triage..."
(cd "$REPO_ROOT" && bash scripts/classify_release_upload.sh "${triage_args[@]}")

cat <<'CHECK'

Manual upload triage check name:
1. Release Upload Triage / Classify Uploaded Release Artifact
CHECK
