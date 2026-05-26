#!/usr/bin/env bash
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

DEFAULT_OUTPUT_REL="dist/skillforge_ai_candidate_2026-05-25.zip"
OUTPUT_REL="${SKILLFORGE_CANDIDATE_OUTPUT_REL:-$DEFAULT_OUTPUT_REL}"
OUTPUT_PATH="$REPO_ROOT/$OUTPUT_REL"
SUMMARY_PATH="$REPO_ROOT/release_artifacts/skillforge_ai_candidate_build_summary.json"

usage() {
  cat <<'USAGE'
Usage: bash scripts/build_skillforge_ai_candidate_zip.sh [--output REL_PATH]

Options:
  --output REL_PATH  Output path relative to repo root (default: dist/skillforge_ai_candidate_2026-05-25.zip)
  -h, --help         Show this help message
USAGE
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --output)
      if [ "$#" -lt 2 ]; then
        echo "Missing value for --output" >&2
        exit 1
      fi
      OUTPUT_REL="$2"
      OUTPUT_PATH="$REPO_ROOT/$OUTPUT_REL"
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

required_inputs=(
  "ToolForge"
  "release_artifacts/skillforge_ai_local_factory_summary.json"
  "release_artifacts/skillforge_ai_test_summary.json"
  "release_artifacts/skillforge_ai_csv_cleaner_e2e_summary.json"
  "release_artifacts/skillforge_ai_validation_summary.json"
)

for item in "${required_inputs[@]}"; do
  if [ ! -e "$REPO_ROOT/$item" ]; then
    echo "Missing required input for candidate build: $item" >&2
    exit 1
  fi
done

mkdir -p "$(dirname "$OUTPUT_PATH")"
rm -f "$OUTPUT_PATH"

zip_excludes=(
  -x ".git/*"
  -x "*/.git/*"
)
for exclude_glob in "${RELEASE_FORBIDDEN_ZIP_EXCLUDES[@]}"; do
  zip_excludes+=(-x "$exclude_glob")
done

(
  cd "$REPO_ROOT"
  zip -rq "$OUTPUT_PATH" "${required_inputs[@]}" "${zip_excludes[@]}"
)

tmp_entries="$(mktemp)"
trap 'rm -f "$tmp_entries"' EXIT
zipinfo -1 "$OUTPUT_PATH" > "$tmp_entries"
if grep -E "$RELEASE_FORBIDDEN_ENTRY_REGEX" "$tmp_entries" >/dev/null; then
  echo "Forbidden entries found in candidate zip:" >&2
  grep -E "$RELEASE_FORBIDDEN_ENTRY_REGEX" "$tmp_entries" >&2
  exit 1
fi

sha256="$(shasum -a 256 "$OUTPUT_PATH" | awk '{print $1}')"

python3 - <<'PY' "$SUMMARY_PATH" "$OUTPUT_REL" "$sha256"
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

summary_path = Path(sys.argv[1])
output_rel = sys.argv[2]
sha256 = sys.argv[3]

payload = {
    "summary_version": "2026-05-25",
    "component": "skillforge_ai",
    "artifact_type": "candidate_zip",
    "generated_at": datetime.now(timezone.utc).isoformat(),
    "overall_status": "passed",
    "output": {
        "path": output_rel,
        "sha256": sha256,
    },
    "contents": [
        "ToolForge/**",
        "release_artifacts/skillforge_ai_local_factory_summary.json",
        "release_artifacts/skillforge_ai_test_summary.json",
        "release_artifacts/skillforge_ai_csv_cleaner_e2e_summary.json",
        "release_artifacts/skillforge_ai_validation_summary.json",
    ],
    "hygiene": {
        "forbidden_entries_found": False,
        "forbidden_policy_file": ".release-config/forbidden_entries.txt",
    },
    "build_command": (
        "bash scripts/build_skillforge_ai_candidate_zip.sh"
    ),
}

summary_path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
print(f"Wrote {summary_path}")
PY

echo "Built SkillForge candidate zip: $OUTPUT_PATH"
echo "SHA256: $sha256"
