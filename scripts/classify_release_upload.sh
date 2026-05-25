#!/usr/bin/env bash
# Classify an uploaded release ZIP as canonical attested pair (when evidence is supplied)
# or unbound wrapper/source bundle, and emit a JSON verdict artifact.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

USER_EXPECTED_RELEASE_NAME="${EXPECTED_RELEASE_NAME:-}"
USER_EXPECTED_RELEASE_SHA="${EXPECTED_RELEASE_SHA:-}"
USER_EXPECTED_EVIDENCE_NAME="${EXPECTED_EVIDENCE_NAME:-}"
USER_EXPECTED_EVIDENCE_SHA="${EXPECTED_EVIDENCE_SHA:-}"

ATTESTATION_ENV_FILE="$SCRIPT_DIR/canonical_release_attestation.env"
if [ ! -f "$ATTESTATION_ENV_FILE" ]; then
  echo "Error: attestation constants file missing: $ATTESTATION_ENV_FILE" >&2
  exit 1
fi
# shellcheck disable=SC1090
source "$ATTESTATION_ENV_FILE"

CANONICAL_RELEASE_NAME="$EXPECTED_RELEASE_NAME"
CANONICAL_RELEASE_SHA="$EXPECTED_RELEASE_SHA"
CANONICAL_EVIDENCE_NAME="$EXPECTED_EVIDENCE_NAME"
CANONICAL_EVIDENCE_SHA="$EXPECTED_EVIDENCE_SHA"

EXPECTED_RELEASE_NAME="${USER_EXPECTED_RELEASE_NAME:-$CANONICAL_RELEASE_NAME}"
EXPECTED_RELEASE_SHA="${USER_EXPECTED_RELEASE_SHA:-$CANONICAL_RELEASE_SHA}"
EXPECTED_EVIDENCE_NAME="${USER_EXPECTED_EVIDENCE_NAME:-$CANONICAL_EVIDENCE_NAME}"
EXPECTED_EVIDENCE_SHA="${USER_EXPECTED_EVIDENCE_SHA:-$CANONICAL_EVIDENCE_SHA}"

RELEASE_PATH="${RELEASE_ZIP_PATH:-}"
EVIDENCE_PATH="${EVIDENCE_ZIP_PATH:-}"
JSON_OUTPUT_PATH="${JSON_OUTPUT_PATH:-}"

usage() {
  cat <<'USAGE'
Usage: bash scripts/classify_release_upload.sh --release PATH [--evidence PATH] [--json-output PATH]

Classifies uploaded artifacts for release governance:
- canonical_release
- clean_new_candidate
- unbound_wrapper_source_bundle
- dirty_archive
- invalid

Options:
  --release PATH      Path to uploaded release ZIP (required)
  --evidence PATH     Path to evidence ZIP (optional; required for canonical attested pair classification)
  --json-output PATH  Write machine-readable verdict JSON to PATH
  -h, --help          Show this help

Environment overrides:
  RELEASE_ZIP_PATH
  EVIDENCE_ZIP_PATH
  JSON_OUTPUT_PATH
  EXPECTED_RELEASE_NAME
  EXPECTED_RELEASE_SHA
  EXPECTED_EVIDENCE_NAME
  EXPECTED_EVIDENCE_SHA

Exit codes:
  0 = canonical_release
  1 = non-canonical (clean_new_candidate, unbound_wrapper_source_bundle, dirty_archive, invalid)
USAGE
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --release)
      if [ "$#" -lt 2 ]; then
        echo "Missing value for --release" >&2
        exit 1
      fi
      RELEASE_PATH="$2"
      shift 2
      ;;
    --evidence)
      if [ "$#" -lt 2 ]; then
        echo "Missing value for --evidence" >&2
        exit 1
      fi
      EVIDENCE_PATH="$2"
      shift 2
      ;;
    --json-output)
      if [ "$#" -lt 2 ]; then
        echo "Missing value for --json-output" >&2
        exit 1
      fi
      JSON_OUTPUT_PATH="$2"
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

if ! command -v shasum >/dev/null 2>&1; then
  echo "Error: shasum is required for SHA256 verification." >&2
  exit 1
fi

if ! command -v zipinfo >/dev/null 2>&1; then
  echo "Error: zipinfo is required for archive entry checks." >&2
  exit 1
fi

if [ ! -f "$RELEASE_PATH" ]; then
  echo "Error: file not found: $RELEASE_PATH" >&2
  exit 1
fi

if [ -n "$EVIDENCE_PATH" ] && [ ! -f "$EVIDENCE_PATH" ]; then
  echo "Error: file not found: $EVIDENCE_PATH" >&2
  exit 1
fi

release_name="$(basename "$RELEASE_PATH")"
release_sha="$(shasum -a 256 "$RELEASE_PATH" | awk '{print $1}')"
release_entries_tmp="$(mktemp)"
forbidden_tmp="$(mktemp)"
reasons_tmp="$(mktemp)"

cleanup() {
  rm -f "$release_entries_tmp" "$forbidden_tmp" "$reasons_tmp"
}
trap cleanup EXIT

zipinfo -1 "$RELEASE_PATH" > "$release_entries_tmp"
grep -E '(^|/)(__MACOSX/|\._|\.DS_Store$)' "$release_entries_tmp" > "$forbidden_tmp" || true
release_forbidden_count="$(wc -l < "$forbidden_tmp" | tr -d ' ')"

required_layout_missing=0
if ! grep -Eq '^(README\.md|ToolForge/|agent-skills-curated/|toolathlon-gym-curated/)' "$release_entries_tmp"; then
  required_layout_missing=1
fi

is_wrapper_name=0
if [[ "$release_name" == *"-main"* ]] || [[ "$release_name" == main*_clean_test.zip ]] || [[ "$release_name" == repair*_clean_test.zip ]]; then
  is_wrapper_name=1
fi

status=1
pair_verification_run=0
pair_verification_passed=0

class_code="invalid"
classification="invalid"
result="Archive is invalid for release policy checks."

if [ "$release_name" != "$EXPECTED_RELEASE_NAME" ]; then
  echo "release filename mismatch" >> "$reasons_tmp"
fi
if [ "$release_sha" != "$EXPECTED_RELEASE_SHA" ]; then
  echo "release hash mismatch" >> "$reasons_tmp"
fi
if [ "$release_forbidden_count" -gt 0 ]; then
  echo "release archive contains forbidden metadata entries" >> "$reasons_tmp"
fi

if [ "$required_layout_missing" -eq 1 ]; then
  echo "missing expected project layout roots" >> "$reasons_tmp"
fi

if [ -z "$EVIDENCE_PATH" ]; then
  echo "evidence ZIP not provided; canonical pair attestation not verified" >> "$reasons_tmp"
else
  pair_verification_run=1
  if (cd "$REPO_ROOT" && bash scripts/verify_release_pair.sh --release "$RELEASE_PATH" --evidence "$EVIDENCE_PATH"); then
    pair_verification_passed=1
    status=0
  else
    echo "release+evidence pair failed canonical attested verification" >> "$reasons_tmp"
  fi
fi

if [ "$status" -eq 0 ]; then
  class_code="canonical_release"
  classification="canonical_release"
  result="canonical attested artifact pair"
elif [ "$required_layout_missing" -eq 1 ]; then
  class_code="invalid"
  classification="invalid"
  result="archive missing expected project layout"
elif [ "$release_forbidden_count" -gt 0 ]; then
  if [ "$is_wrapper_name" -eq 1 ]; then
    class_code="unbound_wrapper_source_bundle"
    classification="unbound_wrapper_source_bundle"
    result="wrapper/source bundle with sidecar metadata"
  else
    class_code="dirty_archive"
    classification="dirty_archive"
    result="forbidden metadata entries present"
  fi
elif [ "$is_wrapper_name" -eq 1 ]; then
  class_code="unbound_wrapper_source_bundle"
  classification="unbound_wrapper_source_bundle"
  result="clean wrapper/source bundle but not attested release"
else
  class_code="clean_new_candidate"
  classification="clean_new_candidate"
  result="clean archive with non-canonical hash; requires fresh evidence"
fi

echo "Release ZIP:                $RELEASE_PATH"
echo "Release name:               $release_name"
echo "Release SHA256:             $release_sha"
echo "Release forbidden entries:  $release_forbidden_count"
if [ -n "$EVIDENCE_PATH" ]; then
  echo "Evidence ZIP:               $EVIDENCE_PATH"
else
  echo "Evidence ZIP:               (not provided)"
fi
echo "Classification:             $classification"
echo "Result:                     $result"

if [ -s "$reasons_tmp" ]; then
  echo "Reasons:"
  while IFS= read -r reason; do
    echo "  - $reason"
  done < "$reasons_tmp"
fi

if [ -n "$JSON_OUTPUT_PATH" ]; then
  mkdir -p "$(dirname "$JSON_OUTPUT_PATH")"

  python - "$JSON_OUTPUT_PATH" "$RELEASE_PATH" "$release_name" "$release_sha" "$release_forbidden_count" "$EVIDENCE_PATH" "$classification" "$result" "$pair_verification_run" "$pair_verification_passed" "$EXPECTED_RELEASE_NAME" "$EXPECTED_RELEASE_SHA" "$EXPECTED_EVIDENCE_NAME" "$EXPECTED_EVIDENCE_SHA" "$reasons_tmp" "$forbidden_tmp" <<'PY'
import json
import sys
from pathlib import Path

(
    output_path,
    release_path,
    release_name,
    release_sha,
    release_forbidden_count,
    evidence_path,
    classification,
    result,
    pair_verification_run,
    pair_verification_passed,
    expected_release_name,
    expected_release_sha,
    expected_evidence_name,
    expected_evidence_sha,
    reasons_file,
    forbidden_file,
) = sys.argv[1:]

reasons = [line.strip() for line in Path(reasons_file).read_text(encoding="utf-8").splitlines() if line.strip()]
forbidden_entries = [line.strip() for line in Path(forbidden_file).read_text(encoding="utf-8").splitlines() if line.strip()]

payload = {
    "release": {
        "path": release_path,
        "name": release_name,
        "sha256": release_sha,
        "forbidden_entry_count": int(release_forbidden_count),
        "forbidden_entries": forbidden_entries,
    },
    "evidence": {
        "path": evidence_path or None,
    },
    "expected": {
        "release": {
            "name": expected_release_name,
            "sha256": expected_release_sha,
        },
        "evidence": {
            "name": expected_evidence_name,
            "sha256": expected_evidence_sha,
        },
    },
    "pair_verification": {
        "was_run": pair_verification_run == "1",
        "passed": pair_verification_passed == "1",
    },
    "classification": classification,
    "class_code": classification,
    "result": result,
    "reasons": reasons,
}

Path(output_path).write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
print(f"Wrote JSON verdict: {output_path}")
PY
fi

if [ "$status" -eq 0 ]; then
  exit 0
fi

exit 1
