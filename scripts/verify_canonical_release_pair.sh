#!/usr/bin/env bash
# Verify that the dist/release/ directory contains the attested canonical
# release + evidence ZIP pair, and that both SHAs match the canonical
# attestation constants.  Also validates that the release is smoke-profile
# scoped and contains no full-profile claims.
#
# Usage: bash scripts/verify_canonical_release_pair.sh [--release-dir DIR]

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

ATTESTATION_ENV_FILE="$SCRIPT_DIR/canonical_release_attestation.env"
if [ ! -f "$ATTESTATION_ENV_FILE" ]; then
  echo "Error: attestation constants file missing: $ATTESTATION_ENV_FILE" >&2
  exit 1
fi
# shellcheck disable=SC1090
source "$ATTESTATION_ENV_FILE"

RELEASE_DIR="$REPO_ROOT/dist/release"

while [ "$#" -gt 0 ]; do
  case "$1" in
    --release-dir)
      RELEASE_DIR="$2"; shift 2 ;;
    -h|--help)
      echo "Usage: bash scripts/verify_canonical_release_pair.sh [--release-dir DIR]"
      exit 0 ;;
    *)
      echo "Unknown argument: $1" >&2; exit 1 ;;
  esac
done

FAILURES=0

fail() { echo "FAIL: $1" >&2; FAILURES=$((FAILURES + 1)); }
pass() { echo "PASS: $1"; }

echo "== Canonical Release Pair Verification =="
echo "Release dir: $RELEASE_DIR"
echo "Expected release:  $EXPECTED_RELEASE_NAME"
echo "Expected evidence: $EXPECTED_EVIDENCE_NAME"
echo ""

# 1. Both ZIPs must exist in dist/release/
RELEASE_ZIP="$RELEASE_DIR/$EXPECTED_RELEASE_NAME"
EVIDENCE_ZIP="$RELEASE_DIR/$EXPECTED_EVIDENCE_NAME"

if [ ! -f "$RELEASE_ZIP" ]; then
  fail "Release ZIP not found: $RELEASE_ZIP"
else
  pass "Release ZIP exists"
fi

if [ ! -f "$EVIDENCE_ZIP" ]; then
  fail "Evidence ZIP not found: $EVIDENCE_ZIP"
else
  pass "Evidence ZIP exists"
fi

# 2. SHA256 of release ZIP must match attestation constant
if [ -f "$RELEASE_ZIP" ]; then
  ACTUAL_RELEASE_SHA="$(shasum -a 256 "$RELEASE_ZIP" | awk '{print $1}')"
  if [ "$ACTUAL_RELEASE_SHA" = "$EXPECTED_RELEASE_SHA" ]; then
    pass "Release ZIP sha256 matches ($EXPECTED_RELEASE_SHA)"
  else
    fail "Release ZIP sha256 mismatch: expected=$EXPECTED_RELEASE_SHA actual=$ACTUAL_RELEASE_SHA"
  fi
fi

# 3. SHA256 of evidence ZIP must match attestation constant
if [ -f "$EVIDENCE_ZIP" ]; then
  ACTUAL_EVIDENCE_SHA="$(shasum -a 256 "$EVIDENCE_ZIP" | awk '{print $1}')"
  if [ "$ACTUAL_EVIDENCE_SHA" = "$EXPECTED_EVIDENCE_SHA" ]; then
    pass "Evidence ZIP sha256 matches ($EXPECTED_EVIDENCE_SHA)"
  else
    fail "Evidence ZIP sha256 mismatch: expected=$EXPECTED_EVIDENCE_SHA actual=$ACTUAL_EVIDENCE_SHA"
  fi
fi

# 4. SHA256SUMS.txt must exist and contain both canonical SHAs
SHA256SUMS="$RELEASE_DIR/SHA256SUMS.txt"
if [ ! -f "$SHA256SUMS" ]; then
  fail "SHA256SUMS.txt missing from release dir"
else
  if grep -q "$EXPECTED_RELEASE_SHA" "$SHA256SUMS"; then
    pass "SHA256SUMS.txt contains canonical release SHA"
  else
    fail "SHA256SUMS.txt missing canonical release SHA"
  fi
  if grep -q "$EXPECTED_EVIDENCE_SHA" "$SHA256SUMS"; then
    pass "SHA256SUMS.txt contains canonical evidence SHA"
  else
    fail "SHA256SUMS.txt missing canonical evidence SHA"
  fi
fi

# 5. RELEASE_STATUS.json canonical_release_sha256 must match
RELEASE_STATUS="$REPO_ROOT/RELEASE_STATUS.json"
if [ ! -f "$RELEASE_STATUS" ]; then
  fail "RELEASE_STATUS.json not found"
else
  STATUS_SHA="$(python3 -c "import json,sys; d=json.load(open(sys.argv[1])); print(d.get('canonical_release_sha256',''))" "$RELEASE_STATUS")"
  if [ "$STATUS_SHA" = "$EXPECTED_RELEASE_SHA" ]; then
    pass "RELEASE_STATUS.json canonical_release_sha256 matches"
  else
    fail "RELEASE_STATUS.json canonical_release_sha256 mismatch: expected=$EXPECTED_RELEASE_SHA got=$STATUS_SHA"
  fi
fi

# 6. canonical_release_attestation.env must reference smoke profile
if [ "${EXPECTED_TOOLATHLON_PROFILE:-}" = "smoke" ]; then
  pass "Attestation env: EXPECTED_TOOLATHLON_PROFILE=smoke"
else
  fail "Attestation env: expected EXPECTED_TOOLATHLON_PROFILE=smoke, got=${EXPECTED_TOOLATHLON_PROFILE:-unset}"
fi

# 7. Release ZIP must NOT contain full-profile *validation result* artifacts
# (source profile definitions are acceptable; only gated run outputs are forbidden)
if [ -f "$RELEASE_ZIP" ]; then
  FULL_PROFILE_RESULTS="$(zipinfo -1 "$RELEASE_ZIP" 2>/dev/null | grep -E 'toolathlon_full_smoke_summary|full_profile_smoke_summary|validation_full_profile' || true)"
  if [ -z "$FULL_PROFILE_RESULTS" ]; then
    pass "Release ZIP contains no full-profile validation result artifacts"
  else
    fail "Release ZIP contains full-profile validation result artifacts (release must be smoke-only): $FULL_PROFILE_RESULTS"
  fi
fi

# 8. Evidence ZIP must contain required smoke-profile validation summary
if [ -f "$EVIDENCE_ZIP" ]; then
  VALIDATION_ENTRY="$(zipinfo -1 "$EVIDENCE_ZIP" 2>/dev/null | grep 'validation_summary.json' || true)"
  if [ -n "$VALIDATION_ENTRY" ]; then
    pass "Evidence ZIP contains validation_summary.json"
  else
    fail "Evidence ZIP missing validation_summary.json"
  fi
fi

echo ""
if [ "$FAILURES" -eq 0 ]; then
  echo "All canonical release pair checks passed."
  exit 0
else
  echo "Canonical release pair verification failed with $FAILURES failure(s)." >&2
  exit 1
fi
