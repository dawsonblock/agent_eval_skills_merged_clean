#!/usr/bin/env bash
# Build a clean release ZIP and verify it excludes macOS metadata and local caches.

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

DIST_DIR="$REPO_ROOT/dist"
TIMESTAMP="$(date -u +%Y%m%dT%H%M%SZ)"
DEFAULT_OUTPUT="$DIST_DIR/agent_eval_skills_merged_clean-$TIMESTAMP.zip"

OUTPUT_PATH="${RELEASE_ZIP_OUTPUT:-$DEFAULT_OUTPUT}"
VALIDATE_ARCHIVE=1
EXPECTED_SHA256="${EXPECTED_RELEASE_SHA256:-}"

usage() {
  cat <<'USAGE'
Usage: bash scripts/create_release_zip.sh [--output PATH] [--skip-validate]

Options:
  --output PATH     Write archive to PATH (default: dist/agent_eval_skills_merged_clean-<timestamp>.zip)
  --skip-validate   Skip post-build forbidden-entry validation
  -h, --help        Show this help message

Environment:
  RELEASE_ZIP_OUTPUT  Same as --output PATH
  EXPECTED_RELEASE_SHA256  If set, fail when archive SHA256 differs
USAGE
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --output)
      if [ "$#" -lt 2 ]; then
        echo "Missing value for --output" >&2
        exit 1
      fi
      OUTPUT_PATH="$2"
      shift 2
      ;;
    --skip-validate)
      VALIDATE_ARCHIVE=0
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

mkdir -p "$(dirname "$OUTPUT_PATH")"

abs_output_path() {
  local target="$1"
  local target_dir
  target_dir="$(cd "$(dirname "$target")" && pwd)"
  printf '%s/%s\n' "$target_dir" "$(basename "$target")"
}

OUTPUT_PATH="$(abs_output_path "$OUTPUT_PATH")"

echo "Repository root: $REPO_ROOT"
echo "Output archive: $OUTPUT_PATH"

cd "$REPO_ROOT"

rm -f "$OUTPUT_PATH"

zip_excludes=(
  -x ".git/*"
  -x "*/.git/*"
  -x "dist/*"
  -x "*/dist/*"
)

for exclude_glob in "${RELEASE_FORBIDDEN_ZIP_EXCLUDES[@]}"; do
  zip_excludes+=(-x "$exclude_glob")
done

zip -rq "$OUTPUT_PATH" . "${zip_excludes[@]}"

if [ "$VALIDATE_ARCHIVE" -eq 1 ]; then
  tmp_forbidden="$(mktemp)"
  trap 'rm -f "$tmp_forbidden"' EXIT

  zipinfo -1 "$OUTPUT_PATH" > "$tmp_forbidden"

  if grep -E "$RELEASE_FORBIDDEN_ENTRY_REGEX" "$tmp_forbidden" >/dev/null; then
    echo "Forbidden entries found in archive:" >&2
    grep -E "$RELEASE_FORBIDDEN_ENTRY_REGEX" "$tmp_forbidden" >&2
    exit 1
  fi

  echo "Archive validation passed (no forbidden metadata/cache entries)."
fi

if command -v du >/dev/null 2>&1; then
  du -h "$OUTPUT_PATH"
fi

if [ -n "$EXPECTED_SHA256" ]; then
  actual_sha="$(shasum -a 256 "$OUTPUT_PATH" | awk '{print $1}')"
  if [ "$actual_sha" != "$EXPECTED_SHA256" ]; then
    echo "Archive hash mismatch." >&2
    echo "Expected: $EXPECTED_SHA256" >&2
    echo "Actual:   $actual_sha" >&2
    exit 1
  fi
  echo "Archive hash matches expected SHA256: $EXPECTED_SHA256"
fi

echo "Created release archive: $OUTPUT_PATH"