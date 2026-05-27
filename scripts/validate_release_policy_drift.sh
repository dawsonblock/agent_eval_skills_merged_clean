#!/usr/bin/env bash
# Validate that canonical release-policy constants have not drifted across docs,
# manifests, and (optionally) current validation logs.

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

require_attestation_value() {
  local var_name="$1"
  local var_value="${!var_name:-}"
  if [ -z "$var_value" ]; then
    echo "Error: required attestation value is missing: $var_name" >&2
    exit 1
  fi
}

for required_var in \
  EXPECTED_RELEASE_NAME \
  EXPECTED_RELEASE_SHA \
  EXPECTED_EVIDENCE_NAME \
  EXPECTED_EVIDENCE_SHA \
  EXPECTED_TOOLATHLON_PROFILE \
  EXPECTED_SMOKE_TARGETS \
  EXPECTED_MCP_PACKAGE_COUNT; do
  require_attestation_value "$required_var"
done

REQUIRE_VALIDATION_LOGS=0

usage() {
  cat <<'USAGE'
Usage: bash scripts/validate_release_policy_drift.sh [--require-validation-logs]

Checks that canonical release policy constants remain consistent across:
- key docs
- evidence manifests
- (optional) current .validation_logs summaries

Options:
  --require-validation-logs  Fail if required .validation_logs summaries are missing
  -h, --help                 Show this help

Exit codes:
  0 = no drift detected
  1 = drift detected or required artifacts missing
USAGE
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --require-validation-logs)
      REQUIRE_VALIDATION_LOGS=1
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

if ! command -v python3 >/dev/null 2>&1; then
  echo "Error: python3 is required." >&2
  exit 1
fi

check_doc_contains() {
  local file_path="$1"
  local needle="$2"
  local label="$3"
  if ! grep -Fq "$needle" "$file_path"; then
    echo "Drift: $label not found in $file_path" >&2
    return 1
  fi
  return 0
}

DOC_FILES=(
  "$REPO_ROOT/README.md"
  "$REPO_ROOT/VALIDATION_EVIDENCE.md"
  "$REPO_ROOT/DEPLOYMENT.md"
  "$REPO_ROOT/WORKSPACE_HEALTH_DASHBOARD.md"
)

missing=0
for file_path in "${DOC_FILES[@]}"; do
  if [ ! -f "$file_path" ]; then
    echo "Error: required document missing: $file_path" >&2
    missing=1
  fi
done
if [ "$missing" -ne 0 ]; then
  exit 1
fi

for file_path in "${DOC_FILES[@]}"; do
  check_doc_contains "$file_path" "$EXPECTED_RELEASE_NAME" "expected release name" || missing=1
  check_doc_contains "$file_path" "$EXPECTED_RELEASE_SHA" "expected release sha" || missing=1
  check_doc_contains "$file_path" "$EXPECTED_EVIDENCE_NAME" "expected evidence name" || missing=1
  check_doc_contains "$file_path" "$EXPECTED_EVIDENCE_SHA" "expected evidence sha" || missing=1
done

# Profile policy appears in README and evidence/dashboard docs.
for file_path in \
  "$REPO_ROOT/README.md" \
  "$REPO_ROOT/VALIDATION_EVIDENCE.md" \
  "$REPO_ROOT/WORKSPACE_HEALTH_DASHBOARD.md"; do
  check_doc_contains "$file_path" "$EXPECTED_TOOLATHLON_PROFILE" "expected Toolathlon profile" || missing=1
done

if [ "$missing" -ne 0 ]; then
  echo "Release-policy doc drift detected." >&2
  exit 1
fi

python3 - "$REPO_ROOT" "$EXPECTED_RELEASE_NAME" "$EXPECTED_RELEASE_SHA" "$EXPECTED_EVIDENCE_NAME" "$EXPECTED_EVIDENCE_SHA" "$EXPECTED_TOOLATHLON_PROFILE" "$EXPECTED_SMOKE_TARGETS" "$EXPECTED_MCP_PACKAGE_COUNT" "$REQUIRE_VALIDATION_LOGS" <<'PY'
import json
import sys
from pathlib import Path

(
    repo_root,
    expected_release_name,
    expected_release_sha,
    expected_evidence_name,
    expected_evidence_sha,
    expected_profile,
    expected_smoke_targets_raw,
    expected_pkg_count,
    require_logs,
) = sys.argv[1:]

root = Path(repo_root)
expected_pkg_count_int = int(expected_pkg_count)
expected_smoke_targets = [item.strip() for item in expected_smoke_targets_raw.split(",") if item.strip()]
require_logs_bool = require_logs == "1"

errors: list[str] = []


def require_sequence(actual, expected, label):
    if actual != expected:
        errors.append(f"{label} mismatch (expected {expected!r}, got {actual!r})")


release_status_path = root / "RELEASE_STATUS.json"
if release_status_path.exists():
    release_status = json.loads(release_status_path.read_text(encoding="utf-8"))
    smoke_targets = release_status.get("smoke_targets")
    if smoke_targets is not None:
        require_sequence(smoke_targets, expected_smoke_targets, f"{release_status_path}:smoke_targets")
  excluded_targets = release_status.get("excluded_smoke_targets")
  if excluded_targets is None:
    excluded_targets = release_status.get("removed_smoke_targets")
  if excluded_targets is not None and "google_calendar" not in excluded_targets:
    errors.append(f"{release_status_path}:excluded_smoke_targets must include 'google_calendar'")

manifest_candidates = [
    root / "RELEASE_EVIDENCE_MANIFEST_2026-05-22.json",
    root / "release_artifacts" / "RELEASE_EVIDENCE_MANIFEST_2026-05-22.json",
]

for manifest_path in manifest_candidates:
    if not manifest_path.exists():
        continue
    try:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception as exc:  # pragma: no cover - defensive
        errors.append(f"{manifest_path}: unreadable json: {exc}")
        continue

    if payload.get("release_zip") != expected_release_name:
        errors.append(
            f"{manifest_path}: release_zip mismatch (expected {expected_release_name!r}, got {payload.get('release_zip')!r})"
        )
    if payload.get("release_zip_sha256") != expected_release_sha:
        errors.append(
            f"{manifest_path}: release_zip_sha256 mismatch (expected {expected_release_sha!r}, got {payload.get('release_zip_sha256')!r})"
        )
    if payload.get("evidence_zip") != expected_evidence_name:
        errors.append(
            f"{manifest_path}: evidence_zip mismatch (expected {expected_evidence_name!r}, got {payload.get('evidence_zip')!r})"
        )
    evidence_sha = payload.get("evidence_zip_sha256")
    if evidence_sha is not None and evidence_sha != expected_evidence_sha:
      errors.append(
        f"{manifest_path}: evidence_zip_sha256 mismatch (expected {expected_evidence_sha!r}, got {evidence_sha!r})"
      )

    artifact_summary = payload.get("toolathlon_artifact_build_summary", {})
    if artifact_summary:
        if artifact_summary.get("profile") != expected_profile:
            errors.append(
                f"{manifest_path}: toolathlon_artifact_build_summary.profile mismatch (expected {expected_profile!r}, got {artifact_summary.get('profile')!r})"
            )
        if artifact_summary.get("expected_package_count") != expected_pkg_count_int:
            errors.append(
                f"{manifest_path}: expected_package_count mismatch (expected {expected_pkg_count_int}, got {artifact_summary.get('expected_package_count')!r})"
            )

validation_logs = root / ".validation_logs"
artifact_summary_path = validation_logs / "toolathlon_artifact_build_summary.json"
validation_summary_path = validation_logs / "validation_summary.json"

if require_logs_bool:
    for required in (artifact_summary_path, validation_summary_path):
        if not required.exists():
            errors.append(f"Missing required validation summary: {required}")

if require_logs_bool and artifact_summary_path.exists():
    artifact_summary = json.loads(artifact_summary_path.read_text(encoding="utf-8"))
    if artifact_summary.get("profile") != expected_profile:
        errors.append(
            f"{artifact_summary_path}: profile mismatch (expected {expected_profile!r}, got {artifact_summary.get('profile')!r})"
        )
    if artifact_summary.get("expected_package_count") != expected_pkg_count_int:
        errors.append(
            f"{artifact_summary_path}: expected_package_count mismatch (expected {expected_pkg_count_int}, got {artifact_summary.get('expected_package_count')!r})"
        )
    if artifact_summary.get("package_count") != expected_pkg_count_int:
        errors.append(
            f"{artifact_summary_path}: package_count mismatch (expected {expected_pkg_count_int}, got {artifact_summary.get('package_count')!r})"
        )
    packages = [item.get("package") for item in artifact_summary.get("packages", []) if isinstance(item, dict)]
    if packages:
        require_sequence(packages, expected_smoke_targets, f"{artifact_summary_path}:packages")

if require_logs_bool and validation_summary_path.exists():
    validation_summary = json.loads(validation_summary_path.read_text(encoding="utf-8"))
    capabilities = validation_summary.get("capabilities", {})
    profile = capabilities.get("toolathlon_profile")
    if profile != expected_profile:
        errors.append(
            f"{validation_summary_path}: capabilities.toolathlon_profile mismatch (expected {expected_profile!r}, got {profile!r})"
        )
    smoke_targets = validation_summary.get("smoke_targets")
    if smoke_targets is not None:
        require_sequence(smoke_targets, expected_smoke_targets, f"{validation_summary_path}:smoke_targets")
    excluded_targets = validation_summary.get("excluded_smoke_targets")
    if excluded_targets is not None and "google_calendar" not in excluded_targets:
        errors.append(f"{validation_summary_path}:excluded_smoke_targets must include 'google_calendar'")

if errors:
    print("Release policy drift detected:", file=sys.stderr)
    for err in errors:
        print(f"- {err}", file=sys.stderr)
    raise SystemExit(1)

print("Release policy drift check passed.")
PY
