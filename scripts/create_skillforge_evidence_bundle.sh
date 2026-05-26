#!/usr/bin/env bash
# Build a SkillForge-specific evidence bundle ZIP from release_artifacts/ and compute SHA256.
#
# Usage:
#   bash scripts/create_skillforge_evidence_bundle.sh [--date YYYYMMDD] [--output PATH] [--skip-validate]

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

FORBIDDEN_POLICY_FILE="$SCRIPT_DIR/release_forbidden_entries.sh"
if [ ! -f "$FORBIDDEN_POLICY_FILE" ]; then
  echo "Error: forbidden-entry policy file missing: $FORBIDDEN_POLICY_FILE" >&2
  exit 1
fi
# shellcheck disable=SC1090
source "$FORBIDDEN_POLICY_FILE"

DATE_TAG="${EVIDENCE_DATE_TAG:-$(date -u +%Y-%m-%d)}"
OUTPUT_PATH=""
VALIDATE_BUNDLE=1

usage() {
  cat <<'USAGE'
Usage: bash scripts/create_skillforge_evidence_bundle.sh [--date YYYYMMDD] [--output PATH] [--skip-validate]

Options:
  --date YYYYMMDD   Date tag for bundle filename (default: current UTC date)
  --output PATH     Write bundle to PATH
                    (default: repo root / agent_eval_skills_merged_clean-skillforge-evidence-<date>.zip)
  --skip-validate   Skip forbidden-entry scan
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
  OUTPUT_PATH="$REPO_ROOT/agent_eval_skills_merged_clean-skillforge-evidence-${DATE_TAG}.zip"
fi

abs_output_path() {
  local target="$1"
  mkdir -p "$(dirname "$target")"
  local target_dir
  target_dir="$(cd "$(dirname "$target")" && pwd)"
  printf '%s/%s\n' "$target_dir" "$(basename "$target")"
}

OUTPUT_PATH="$(abs_output_path "$OUTPUT_PATH")"

required_files=(
  "release_artifacts/skillforge_ai_candidate_build_summary.json"
  "release_artifacts/skillforge_ai_local_factory_summary.json"
  "release_artifacts/skillforge_ai_test_summary.json"
  "release_artifacts/skillforge_ai_csv_cleaner_e2e_summary.json"
  "release_artifacts/skillforge_ai_validation_summary.json"
  "release_artifacts/RELEASE_EVIDENCE_APPENDIX.md"
  "RELEASE_EVIDENCE_APPENDIX.md"
)

FILES_TO_BUNDLE=()
missing_required=()

for rel in "${required_files[@]}"; do
  if [ -f "$REPO_ROOT/$rel" ]; then
    FILES_TO_BUNDLE+=("$rel")
  else
    missing_required+=("$rel")
  fi
done

if [ "${#missing_required[@]}" -gt 0 ]; then
  echo "Error: missing required SkillForge evidence files:" >&2
  for item in "${missing_required[@]}"; do
    echo "  $item" >&2
  done
  exit 1
fi

echo "Repository root  : $REPO_ROOT"
echo "Output bundle    : $OUTPUT_PATH"
echo "Date tag         : $DATE_TAG"
echo ""
echo "Bundling ${#FILES_TO_BUNDLE[@]} SkillForge evidence file(s):"
for f in "${FILES_TO_BUNDLE[@]}"; do
  echo "  $f"
done
echo ""

rm -f "$OUTPUT_PATH"

cd "$REPO_ROOT"
zip -q "$OUTPUT_PATH" "${FILES_TO_BUNDLE[@]}"

if [ "$VALIDATE_BUNDLE" -eq 1 ]; then
  tmp_entries="$(mktemp)"
  trap 'rm -f "$tmp_entries"' EXIT

  zipinfo -1 "$OUTPUT_PATH" > "$tmp_entries"

  if grep -E "$RELEASE_FORBIDDEN_ENTRY_REGEX" "$tmp_entries" >/dev/null; then
    echo "Forbidden entries found in SkillForge evidence bundle:" >&2
    grep -E "$RELEASE_FORBIDDEN_ENTRY_REGEX" "$tmp_entries" >&2
    exit 1
  fi

  echo "Bundle validation passed (no forbidden entries)."
fi

if command -v du >/dev/null 2>&1; then
  du -h "$OUTPUT_PATH"
fi

echo "Created SkillForge evidence bundle: $OUTPUT_PATH"
echo ""
echo "SHA256:"
shasum -a 256 "$OUTPUT_PATH"
