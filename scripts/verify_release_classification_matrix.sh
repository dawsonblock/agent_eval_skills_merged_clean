#!/usr/bin/env bash
# Verify release-upload classification matrix across all expected classes.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

USER_EXPECTED_RELEASE_NAME="${EXPECTED_RELEASE_NAME:-}"
USER_EXPECTED_EVIDENCE_NAME="${EXPECTED_EVIDENCE_NAME:-}"

ATTESTATION_ENV_FILE="$SCRIPT_DIR/canonical_release_attestation.env"
if [ ! -f "$ATTESTATION_ENV_FILE" ]; then
  echo "Error: attestation constants file missing: $ATTESTATION_ENV_FILE" >&2
  exit 1
fi
# shellcheck disable=SC1090
source "$ATTESTATION_ENV_FILE"

CANONICAL_RELEASE_NAME="$EXPECTED_RELEASE_NAME"
CANONICAL_EVIDENCE_NAME="$EXPECTED_EVIDENCE_NAME"

EXPECTED_RELEASE_NAME="${USER_EXPECTED_RELEASE_NAME:-$CANONICAL_RELEASE_NAME}"
EXPECTED_EVIDENCE_NAME="${USER_EXPECTED_EVIDENCE_NAME:-$CANONICAL_EVIDENCE_NAME}"

CANONICAL_RELEASE_PATH="${CANONICAL_RELEASE_PATH:-$REPO_ROOT/$EXPECTED_RELEASE_NAME}"
if [ ! -f "$CANONICAL_RELEASE_PATH" ] && [ -f "$REPO_ROOT/../$EXPECTED_RELEASE_NAME" ]; then
  CANONICAL_RELEASE_PATH="$REPO_ROOT/../$EXPECTED_RELEASE_NAME"
fi

CANONICAL_EVIDENCE_PATH="${CANONICAL_EVIDENCE_PATH:-$REPO_ROOT/$EXPECTED_EVIDENCE_NAME}"
if [ ! -f "$CANONICAL_EVIDENCE_PATH" ] && [ -f "$REPO_ROOT/../$EXPECTED_EVIDENCE_NAME" ]; then
  CANONICAL_EVIDENCE_PATH="$REPO_ROOT/../$EXPECTED_EVIDENCE_NAME"
fi

if [ ! -f "$CANONICAL_RELEASE_PATH" ]; then
  echo "Error: canonical release ZIP not found: $CANONICAL_RELEASE_PATH" >&2
  exit 1
fi

if [ ! -f "$CANONICAL_EVIDENCE_PATH" ]; then
  echo "Error: canonical evidence ZIP not found: $CANONICAL_EVIDENCE_PATH" >&2
  exit 1
fi

TMP_DIR="$(mktemp -d "${TMPDIR:-/tmp}/release-matrix.XXXXXX")"
cleanup() {
  rm -rf "$TMP_DIR"
}
trap cleanup EXIT

create_zip() {
  local zip_path="$1"
  local entries_json="$2"

  python3 - "$zip_path" "$entries_json" <<'PYEOF'
import json
import zipfile
import sys

zip_path = sys.argv[1]
entries = json.loads(sys.argv[2])
with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
    for name, content in entries.items():
        zf.writestr(name, content)
PYEOF
}

run_case() {
  local case_name="$1"
  local expected_class="$2"
  local expected_status="$3"
  local release_path="$4"
  local evidence_path="${5:-}"

  local verdict_path="$TMP_DIR/${case_name}.json"
  local args=(--release "$release_path" --json-output "$verdict_path")
  if [ -n "$evidence_path" ]; then
    args+=(--evidence "$evidence_path")
  fi

  local exit_code=0
  set +e
  (cd "$REPO_ROOT" && bash scripts/classify_release_upload.sh "${args[@]}")
  exit_code=$?
  set -e

  local actual_class
  actual_class="$(python3 - "$verdict_path" <<'PYEOF'
import json
import sys
with open(sys.argv[1], 'r', encoding='utf-8') as fh:
    payload = json.load(fh)
print(payload.get('classification', ''))
PYEOF
)"

  if [ "$actual_class" != "$expected_class" ]; then
    echo "Case '$case_name' failed: expected class '$expected_class', got '$actual_class'" >&2
    exit 1
  fi

  if [ "$exit_code" -ne "$expected_status" ]; then
    echo "Case '$case_name' failed: expected exit $expected_status, got $exit_code" >&2
    exit 1
  fi

  echo "✓ $case_name => $actual_class (exit=$exit_code)"
}

# Case: canonical_release
run_case \
  "canonical_release" \
  "canonical_release" \
  0 \
  "$CANONICAL_RELEASE_PATH" \
  "$CANONICAL_EVIDENCE_PATH"

# Case: clean_new_candidate
CLEAN_CANDIDATE_ZIP="$TMP_DIR/agent_eval_skills_merged_clean-pruned-smoke-new-candidate.zip"
create_zip "$CLEAN_CANDIDATE_ZIP" '{"README.md":"candidate\n"}'
run_case \
  "clean_new_candidate" \
  "clean_new_candidate" \
  1 \
  "$CLEAN_CANDIDATE_ZIP"

# Case: unbound_wrapper_source_bundle
WRAPPER_ZIP="$TMP_DIR/agent_eval_skills_merged_clean-main_clean_test.zip"
create_zip "$WRAPPER_ZIP" '{"README.md":"wrapper\n"}'
run_case \
  "unbound_wrapper_source_bundle" \
  "unbound_wrapper_source_bundle" \
  1 \
  "$WRAPPER_ZIP"

# Case: dirty_archive
DIRTY_ZIP="$TMP_DIR/agent_eval_skills_merged_clean-dirty.zip"
create_zip "$DIRTY_ZIP" '{"README.md":"dirty\n","__MACOSX/._junk":"meta"}'
run_case \
  "dirty_archive" \
  "dirty_archive" \
  1 \
  "$DIRTY_ZIP"

# Case: invalid (missing expected layout roots)
INVALID_ZIP="$TMP_DIR/not-a-release.zip"
create_zip "$INVALID_ZIP" '{"notes.txt":"invalid\n"}'
run_case \
  "invalid" \
  "invalid" \
  1 \
  "$INVALID_ZIP"

echo "Release classification matrix verification passed."
