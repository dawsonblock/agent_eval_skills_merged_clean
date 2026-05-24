#!/usr/bin/env bash
# Verify whether a release+evidence ZIP pair matches the canonical attested hashes.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

EXPECTED_RELEASE_NAME_DEFAULT="agent_eval_skills_merged_clean-pruned-smoke.zip"
EXPECTED_RELEASE_SHA_DEFAULT="74b34edf25141c8f96bbf03975ed8e6675dd3f574d962be2921278295544b189"
EXPECTED_EVIDENCE_NAME_DEFAULT="agent_eval_skills_merged_clean-smoke-evidence-2026-05-22.zip"
EXPECTED_EVIDENCE_SHA_DEFAULT="5d2e43a0d6e961f99209fab0c55e3c11c5795228200974315f44bdb5e608426c"

EXPECTED_RELEASE_NAME="${EXPECTED_RELEASE_NAME:-$EXPECTED_RELEASE_NAME_DEFAULT}"
EXPECTED_RELEASE_SHA="${EXPECTED_RELEASE_SHA:-$EXPECTED_RELEASE_SHA_DEFAULT}"
EXPECTED_EVIDENCE_NAME="${EXPECTED_EVIDENCE_NAME:-$EXPECTED_EVIDENCE_NAME_DEFAULT}"
EXPECTED_EVIDENCE_SHA="${EXPECTED_EVIDENCE_SHA:-$EXPECTED_EVIDENCE_SHA_DEFAULT}"

DEFAULT_RELEASE_PATH="$REPO_ROOT/$EXPECTED_RELEASE_NAME"
DEFAULT_EVIDENCE_PATH="$REPO_ROOT/$EXPECTED_EVIDENCE_NAME"
if [ ! -f "$DEFAULT_RELEASE_PATH" ] && [ -f "$REPO_ROOT/../$EXPECTED_RELEASE_NAME" ]; then
  DEFAULT_RELEASE_PATH="$REPO_ROOT/../$EXPECTED_RELEASE_NAME"
fi
if [ ! -f "$DEFAULT_EVIDENCE_PATH" ] && [ -f "$REPO_ROOT/../$EXPECTED_EVIDENCE_NAME" ]; then
  DEFAULT_EVIDENCE_PATH="$REPO_ROOT/../$EXPECTED_EVIDENCE_NAME"
fi

RELEASE_PATH="${RELEASE_ZIP_PATH:-$DEFAULT_RELEASE_PATH}"
EVIDENCE_PATH="${EVIDENCE_ZIP_PATH:-$DEFAULT_EVIDENCE_PATH}"

usage() {
  cat <<'USAGE'
Usage: bash scripts/verify_release_pair.sh [--release PATH] [--evidence PATH]

Checks both filename and SHA256 against canonical 2026-05-22 attestation values.

Options:
  --release PATH   Path to release ZIP
  --evidence PATH  Path to evidence ZIP
  -h, --help       Show this help

Environment overrides:
  RELEASE_ZIP_PATH
  EVIDENCE_ZIP_PATH
  EXPECTED_RELEASE_NAME
  EXPECTED_RELEASE_SHA
  EXPECTED_EVIDENCE_NAME
  EXPECTED_EVIDENCE_SHA

Exit codes:
  0 = canonical attested pair
  1 = unbound wrapper/source bundle (or mismatched evidence pair)
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

if ! command -v shasum >/dev/null 2>&1; then
  echo "Error: shasum is required for SHA256 verification." >&2
  exit 1
fi

if ! command -v zipinfo >/dev/null 2>&1; then
  echo "Error: zipinfo is required for archive entry checks." >&2
  exit 1
fi

if ! command -v python3 >/dev/null 2>&1; then
  echo "Error: python3 is required for evidence bundle verification." >&2
  exit 1
fi

for p in "$RELEASE_PATH" "$EVIDENCE_PATH"; do
  if [ ! -f "$p" ]; then
    echo "Error: file not found: $p" >&2
    exit 1
  fi
done

release_name="$(basename "$RELEASE_PATH")"
evidence_name="$(basename "$EVIDENCE_PATH")"
release_sha="$(shasum -a 256 "$RELEASE_PATH" | awk '{print $1}')"
evidence_sha="$(shasum -a 256 "$EVIDENCE_PATH" | awk '{print $1}')"

check_forbidden_entries() {
  local zip_path="$1"
  local tmp_entries
  tmp_entries="$(mktemp)"
  zipinfo -1 "$zip_path" > "$tmp_entries"
  if grep -E '(^|/)(__MACOSX/|\._|\.DS_Store$)' "$tmp_entries" >/dev/null; then
    echo "Forbidden metadata entries found in: $zip_path" >&2
    grep -E '(^|/)(__MACOSX/|\._|\.DS_Store$)' "$tmp_entries" >&2
    rm -f "$tmp_entries"
    return 1
  fi
  rm -f "$tmp_entries"
  return 0
}

check_manifest_hash_agreement() {
  local evidence_zip="$1"
  local expected_release_name="$2"
  local expected_release_sha="$3"
  local expected_evidence_name="$4"
  local expected_evidence_sha="$5"

  python3 - "$evidence_zip" "$expected_release_name" "$expected_release_sha" "$expected_evidence_name" "$expected_evidence_sha" <<'PYEOF'
import json
import sys
import zipfile

zip_path, exp_release_name, exp_release_sha, exp_evidence_name, exp_evidence_sha = sys.argv[1:]

manifest_candidates = [
    "release_artifacts/RELEASE_EVIDENCE_MANIFEST_2026-05-22.json",
    "RELEASE_EVIDENCE_MANIFEST_2026-05-22.json",
]

with zipfile.ZipFile(zip_path, "r") as zf:
    manifest_name = next((m for m in manifest_candidates if m in zf.namelist()), None)
    if manifest_name is None:
        raise SystemExit("manifest_missing")

    try:
        manifest = json.loads(zf.read(manifest_name).decode("utf-8"))
    except Exception as exc:
        raise SystemExit(f"manifest_parse_error:{exc}") from exc

release_name = (
    manifest.get("release_zip")
    or manifest.get("archive", {}).get("path")
)
release_sha = (
    manifest.get("release_zip_sha256")
    or manifest.get("archive_sha256")
    or manifest.get("archive", {}).get("sha256")
)
evidence_name = manifest.get("evidence_zip")
evidence_sha = manifest.get("evidence_zip_sha256")

errors = []
if release_name != exp_release_name:
    errors.append(f"release_name:{release_name!r}!=expected:{exp_release_name!r}")
if release_sha != exp_release_sha:
    errors.append(f"release_sha:{release_sha!r}!=expected:{exp_release_sha!r}")

# Older manifests may not have evidence_* fields; only enforce when present.
if evidence_name is not None and evidence_name != exp_evidence_name:
    errors.append(f"evidence_name:{evidence_name!r}!=expected:{exp_evidence_name!r}")
if evidence_sha is not None and evidence_sha != exp_evidence_sha:
    errors.append(f"evidence_sha:{evidence_sha!r}!=expected:{exp_evidence_sha!r}")

if errors:
    raise SystemExit("manifest_mismatch:" + "; ".join(errors))

raise SystemExit(0)
PYEOF
}

status=0
notes=()

if [ "$release_name" != "$EXPECTED_RELEASE_NAME" ]; then
  status=1
  notes+=("release filename mismatch")
fi
if [ "$evidence_name" != "$EXPECTED_EVIDENCE_NAME" ]; then
  status=1
  notes+=("evidence filename mismatch")
fi
if [ "$release_sha" != "$EXPECTED_RELEASE_SHA" ]; then
  status=1
  notes+=("release hash mismatch")
fi
if [ "$evidence_sha" != "$EXPECTED_EVIDENCE_SHA" ]; then
  status=1
  notes+=("evidence hash mismatch")
fi
if ! check_forbidden_entries "$RELEASE_PATH"; then
  status=1
  notes+=("release archive contains forbidden metadata entries")
fi
if ! check_forbidden_entries "$EVIDENCE_PATH"; then
  status=1
  notes+=("evidence archive contains forbidden metadata entries")
fi

if ! (cd "$REPO_ROOT" && bash scripts/verify_evidence_bundle.sh --evidence "$EVIDENCE_PATH"); then
  status=1
  notes+=("evidence bundle content/value verification failed")
fi

if ! check_manifest_hash_agreement "$EVIDENCE_PATH" "$EXPECTED_RELEASE_NAME" "$EXPECTED_RELEASE_SHA" "$EXPECTED_EVIDENCE_NAME" "$EXPECTED_EVIDENCE_SHA"; then
  status=1
  notes+=("manifest hash agreement failed")
fi

echo "Release ZIP:   $RELEASE_PATH"
echo "Release name:  $release_name"
echo "Release SHA:   $release_sha"
echo "Evidence ZIP:  $EVIDENCE_PATH"
echo "Evidence name: $evidence_name"
echo "Evidence SHA:  $evidence_sha"

if [ "$status" -eq 0 ]; then
  echo
  echo "Classification: agent_eval_skills_merged_clean — pruned smoke release candidate for controlled testing"
  echo "Result: canonical attested artifact pair"
  exit 0
fi

echo
echo "Classification: Unbound wrapper/source bundle."
echo "Result: not the final attested release artifact"
if [ "${#notes[@]}" -gt 0 ]; then
  echo "Reasons:"
  for item in "${notes[@]}"; do
    echo "  - $item"
  done
fi
exit 1