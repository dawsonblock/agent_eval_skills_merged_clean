#!/usr/bin/env bash
# Build a dated evidence bundle ZIP from release_artifacts/ and compute its SHA256.
#
# Usage:
#   bash scripts/create_evidence_bundle.sh [--date YYYYMMDD] [--output PATH] [--skip-validate]
#
# The bundle includes:
#   - All JSON validation summaries in release_artifacts/
#   - RELEASE_EVIDENCE_MANIFEST_<date>.json
#   - RELEASE_HANDOFF_<date>.md
#   - RELEASE_EVIDENCE_APPENDIX.md
#   - Any RELEASE_ATTESTATION_<date>.md found at the repo root

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

DATE_TAG="$(date -u +%Y-%m-%d)"
OUTPUT_PATH=""
VALIDATE_BUNDLE=1

usage() {
  cat <<'USAGE'
Usage: bash scripts/create_evidence_bundle.sh [--date YYYYMMDD] [--output PATH] [--skip-validate]

Options:
  --date YYYYMMDD   Date tag for the bundle (default: today UTC in YYYYMMDD format)
  --output PATH     Write bundle to PATH (default: repo root / agent_eval_skills_merged_clean-smoke-evidence-<date>.zip)
  --skip-validate   Skip post-build forbidden-entry scan
  -h, --help        Show this help message
USAGE
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --date)
      if [ "$#" -lt 2 ]; then
        echo "Missing value for --date" >&2
        exit 1
      fi
      # Accept YYYYMMDD and reformat to YYYY-MM-DD for display; store raw for filename
      raw_date="$2"
      if [ "${#raw_date}" -eq 8 ]; then
        DATE_TAG="${raw_date:0:4}-${raw_date:4:2}-${raw_date:6:2}"
      else
        DATE_TAG="$raw_date"
      fi
      shift 2
      ;;
    --output)
      if [ "$#" -lt 2 ]; then
        echo "Missing value for --output" >&2
        exit 1
      fi
      OUTPUT_PATH="$2"
      shift 2
      ;;
    --skip-validate)
      VALIDATE_BUNDLE=0
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

if [ -z "$OUTPUT_PATH" ]; then
  OUTPUT_PATH="$REPO_ROOT/agent_eval_skills_merged_clean-smoke-evidence-${DATE_TAG}.zip"
fi

# Resolve to absolute path
abs_output_path() {
  local target="$1"
  mkdir -p "$(dirname "$target")"
  local target_dir
  target_dir="$(cd "$(dirname "$target")" && pwd)"
  printf '%s/%s\n' "$target_dir" "$(basename "$target")"
}

OUTPUT_PATH="$(abs_output_path "$OUTPUT_PATH")"

ARTIFACTS_DIR="$REPO_ROOT/release_artifacts"

if [ ! -d "$ARTIFACTS_DIR" ]; then
  echo "Error: release_artifacts/ directory not found at $ARTIFACTS_DIR" >&2
  exit 1
fi

echo "Repository root  : $REPO_ROOT"
echo "Artifacts source : $ARTIFACTS_DIR"
echo "Output bundle    : $OUTPUT_PATH"
echo "Date tag         : $DATE_TAG"

rm -f "$OUTPUT_PATH"

# Build list of files to include
FILES_TO_BUNDLE=()

# JSON validation summaries
for f in \
  validation_summary.json \
  toolathlon_artifact_build_summary.json \
  toolathlon_mcp_smoke_summary.json \
  toolathlon_preflight_summary.json \
  docker_mcp_smoke_summary.json \
  docker_preflight_summary.json; do
  if [ -f "$ARTIFACTS_DIR/$f" ]; then
    FILES_TO_BUNDLE+=("release_artifacts/$f")
  else
    echo "Warning: expected evidence file missing: release_artifacts/$f" >&2
  fi
done

# Dated manifest — match by date tag (YYYY-MM-DD form)
for f in "$ARTIFACTS_DIR"/RELEASE_EVIDENCE_MANIFEST_*.json; do
  [ -f "$f" ] && FILES_TO_BUNDLE+=("release_artifacts/$(basename "$f")")
done

# Dated handoff notes
for f in "$ARTIFACTS_DIR"/RELEASE_HANDOFF_*.md; do
  [ -f "$f" ] && FILES_TO_BUNDLE+=("release_artifacts/$(basename "$f")")
done

# Appendix
if [ -f "$ARTIFACTS_DIR/RELEASE_EVIDENCE_APPENDIX.md" ]; then
  FILES_TO_BUNDLE+=("release_artifacts/RELEASE_EVIDENCE_APPENDIX.md")
fi

# Attestation at repo root
for f in "$REPO_ROOT"/RELEASE_ATTESTATION_*.md; do
  [ -f "$f" ] && FILES_TO_BUNDLE+=("$(basename "$f")")
done

if [ "${#FILES_TO_BUNDLE[@]}" -eq 0 ]; then
  echo "Error: no evidence files found to bundle" >&2
  exit 1
fi

echo ""
echo "Bundling ${#FILES_TO_BUNDLE[@]} evidence file(s):"
for f in "${FILES_TO_BUNDLE[@]}"; do
  echo "  $f"
done
echo ""

cd "$REPO_ROOT"
zip -q "$OUTPUT_PATH" "${FILES_TO_BUNDLE[@]}"

if [ "$VALIDATE_BUNDLE" -eq 1 ]; then
  tmp_entries="$(mktemp)"
  trap 'rm -f "$tmp_entries"' EXIT

  zipinfo -1 "$OUTPUT_PATH" > "$tmp_entries"

  if grep -E '(^|/)(__MACOSX/|\._|\.DS_Store$|node_modules/|\.validation_logs/|__pycache__/)' "$tmp_entries" >/dev/null; then
    echo "Forbidden entries found in evidence bundle:" >&2
    grep -E '(^|/)(__MACOSX/|\._|\.DS_Store$|node_modules/|\.validation_logs/|__pycache__/)' "$tmp_entries" >&2
    exit 1
  fi

  echo "Bundle validation passed (no forbidden entries)."
fi

if command -v du >/dev/null 2>&1; then
  du -h "$OUTPUT_PATH"
fi

echo "Created evidence bundle: $OUTPUT_PATH"
echo ""
echo "SHA256:"
shasum -a 256 "$OUTPUT_PATH"
