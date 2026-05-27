#!/usr/bin/env bash
# shellcheck shell=bash disable=SC2250,SC2292
# trunk-ignore-all(shellcheck)
# Verify evidence ZIP contains required files and required smoke-profile values.

set -euo pipefail

EVIDENCE_PATH="${EVIDENCE_ZIP_PATH:-}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

FORBIDDEN_POLICY_FILE="$SCRIPT_DIR/release_forbidden_entries.sh"
if [ ! -f "$FORBIDDEN_POLICY_FILE" ]; then
  echo "Error: forbidden-entry policy file missing: $FORBIDDEN_POLICY_FILE" >&2
  exit 1
fi
# shellcheck disable=SC1090
source "$FORBIDDEN_POLICY_FILE"

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

for required_var in EXPECTED_RELEASE_NAME EXPECTED_RELEASE_SHA EXPECTED_EVIDENCE_NAME EXPECTED_EVIDENCE_SHA EXPECTED_TOOLATHLON_PROFILE EXPECTED_MCP_PACKAGE_COUNT EXPECTED_SMOKE_TARGETS EXPECTED_FULL_PROFILE_VALIDATED EXPECTED_PYTHON_VERSION MAX_EVIDENCE_AGE_DAYS; do
  require_attestation_value "$required_var"
done

CANONICAL_RELEASE_NAME="$EXPECTED_RELEASE_NAME"
CANONICAL_RELEASE_SHA="$EXPECTED_RELEASE_SHA"
CANONICAL_EVIDENCE_NAME="$EXPECTED_EVIDENCE_NAME"
CANONICAL_EVIDENCE_SHA="$EXPECTED_EVIDENCE_SHA"

EXPECTED_RELEASE_NAME="$CANONICAL_RELEASE_NAME"
EXPECTED_RELEASE_SHA="$CANONICAL_RELEASE_SHA"
EXPECTED_EVIDENCE_NAME="$CANONICAL_EVIDENCE_NAME"
EXPECTED_EVIDENCE_SHA="$CANONICAL_EVIDENCE_SHA"

export EXPECTED_RELEASE_NAME EXPECTED_RELEASE_SHA EXPECTED_EVIDENCE_NAME EXPECTED_EVIDENCE_SHA
export EXPECTED_TOOLATHLON_PROFILE EXPECTED_MCP_PACKAGE_COUNT EXPECTED_SMOKE_TARGETS EXPECTED_FULL_PROFILE_VALIDATED EXPECTED_PYTHON_VERSION MAX_EVIDENCE_AGE_DAYS

usage() {
  cat <<'USAGE'
Usage: bash scripts/verify_evidence_bundle.sh --evidence PATH

Validates an evidence bundle for smoke-profile release policy:
- Required evidence files exist in the ZIP.
- Required JSON fields/values match expected smoke release criteria.
- Forbidden metadata/cache entries are absent.

Options:
  --evidence PATH   Path to evidence ZIP (required)
  -h, --help        Show this help

Environment overrides:
  EVIDENCE_ZIP_PATH

Exit codes:
  0 = evidence bundle satisfies required policy checks
  1 = missing files, forbidden entries, parse errors, or value mismatches
USAGE
}

while [ "$#" -gt 0 ]; do
  case "$1" in
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

if [ -z "$EVIDENCE_PATH" ]; then
  echo "Error: --evidence is required" >&2
  usage >&2
  exit 1
fi

if [ ! -f "$EVIDENCE_PATH" ]; then
  echo "Error: file not found: $EVIDENCE_PATH" >&2
  exit 1
fi

if ! command -v python3 >/dev/null 2>&1; then
  echo "Error: python3 is required for evidence ZIP validation." >&2
  exit 1
fi

if ! command -v zipinfo >/dev/null 2>&1; then
  echo "Error: zipinfo is required for evidence ZIP validation." >&2
  exit 1
fi

entries_tmp="$(mktemp)"
forbidden_tmp="$(mktemp)"
cleanup_entries() {
  rm -f "$entries_tmp" "$forbidden_tmp"
}
trap cleanup_entries EXIT

zipinfo -1 "$EVIDENCE_PATH" > "$entries_tmp"
grep -E "$RELEASE_FORBIDDEN_ENTRY_REGEX" "$entries_tmp" > "$forbidden_tmp" || true
if [ -s "$forbidden_tmp" ]; then
  echo "forbidden entries found: $(paste -sd ', ' "$forbidden_tmp")" >&2
  exit 1
fi

python3 - "$EVIDENCE_PATH" <<'PYEOF'
import json
import os
import sys
import zipfile
from datetime import datetime, timezone

zip_path = sys.argv[1]

EXPECTED_RELEASE_NAME = os.environ.get(
  "EXPECTED_RELEASE_NAME",
)
EXPECTED_RELEASE_SHA = os.environ.get(
  "EXPECTED_RELEASE_SHA",
)
EXPECTED_EVIDENCE_NAME = os.environ.get(
  "EXPECTED_EVIDENCE_NAME",
)
EXPECTED_EVIDENCE_SHA = os.environ.get(
  "EXPECTED_EVIDENCE_SHA",
)
EXPECTED_TOOLATHLON_PROFILE = os.environ.get("EXPECTED_TOOLATHLON_PROFILE")
EXPECTED_MCP_PACKAGE_COUNT = int(os.environ.get("EXPECTED_MCP_PACKAGE_COUNT", "0"))
EXPECTED_SMOKE_TARGETS = [
  item.strip()
  for item in os.environ.get("EXPECTED_SMOKE_TARGETS", "").split(",")
  if item.strip()
]
EXPECTED_FULL_PROFILE_VALIDATED_RAW = os.environ.get("EXPECTED_FULL_PROFILE_VALIDATED")
EXPECTED_PYTHON_VERSION = os.environ.get("EXPECTED_PYTHON_VERSION")
MAX_EVIDENCE_AGE_DAYS = int(os.environ.get("MAX_EVIDENCE_AGE_DAYS", "0"))


def parse_bool(raw):
  if raw == "true":
    return True
  if raw == "false":
    return False
  return None


EXPECTED_FULL_PROFILE_VALIDATED = parse_bool(EXPECTED_FULL_PROFILE_VALIDATED_RAW)

required_env_values = {
    "EXPECTED_RELEASE_NAME": EXPECTED_RELEASE_NAME,
    "EXPECTED_RELEASE_SHA": EXPECTED_RELEASE_SHA,
    "EXPECTED_EVIDENCE_NAME": EXPECTED_EVIDENCE_NAME,
    "EXPECTED_EVIDENCE_SHA": EXPECTED_EVIDENCE_SHA,
    "EXPECTED_TOOLATHLON_PROFILE": EXPECTED_TOOLATHLON_PROFILE,
    "EXPECTED_PYTHON_VERSION": EXPECTED_PYTHON_VERSION,
}
missing_env = [k for k, v in required_env_values.items() if not isinstance(v, str) or not v.strip()]
if EXPECTED_MCP_PACKAGE_COUNT <= 0:
    missing_env.append("EXPECTED_MCP_PACKAGE_COUNT")
if not EXPECTED_SMOKE_TARGETS:
  missing_env.append("EXPECTED_SMOKE_TARGETS")
if EXPECTED_FULL_PROFILE_VALIDATED is None:
  missing_env.append("EXPECTED_FULL_PROFILE_VALIDATED")
if MAX_EVIDENCE_AGE_DAYS <= 0:
    missing_env.append("MAX_EVIDENCE_AGE_DAYS")
if missing_env:
    raise SystemExit("missing_required_env:" + ",".join(sorted(set(missing_env))))

required_files = [
    "release_artifacts/validation_summary.json",
    "release_artifacts/toolathlon_artifact_build_summary.json",
    "release_artifacts/toolathlon_mcp_smoke_summary.json",
    "release_artifacts/toolathlon_preflight_summary.json",
    "release_artifacts/RELEASE_EVIDENCE_MANIFEST_2026-05-22.json",
    "release_artifacts/RELEASE_HANDOFF_2026-05-22.md",
    "release_artifacts/RELEASE_EVIDENCE_APPENDIX.md",
]

def get_in(data, path):
    current = data
    for key in path:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current

def require(data, path, expected, errors, label):
    actual = get_in(data, path)
    if actual != expected:
        dotted = ".".join(path)
        errors.append(f"{label}:{dotted} expected {expected!r}, got {actual!r}")


def require_sequence(actual, expected, errors, label):
  if actual != expected:
    errors.append(f"{label} expected {expected!r}, got {actual!r}")


def parse_iso8601(value):
    if not isinstance(value, str) or not value.strip():
        return None
    raw = value.strip()
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(raw)
    except ValueError:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def require_recent_iso8601(value, errors, label):
    dt = parse_iso8601(value)
    if dt is None:
        errors.append(f"{label} must be a valid ISO8601 timestamp, got {value!r}")
        return
    age_days = (datetime.now(timezone.utc) - dt).total_seconds() / 86400.0
    if age_days > MAX_EVIDENCE_AGE_DAYS:
        errors.append(
            f"{label} is too old ({age_days:.2f} days > {MAX_EVIDENCE_AGE_DAYS} days)"
        )

errors = []

with zipfile.ZipFile(zip_path, "r") as zf:
    entries = zf.namelist()

    missing = [name for name in required_files if name not in entries]
    if missing:
        errors.append("missing required evidence files: " + ", ".join(missing))

    def read_json(path):
        try:
            with zf.open(path) as f:
                return json.load(f)
        except KeyError:
            return None
        except Exception as exc:
            errors.append(f"failed parsing {path}: {exc}")
            return None

    validation_summary = read_json("release_artifacts/validation_summary.json")
    if validation_summary is not None:
        require(validation_summary, ["overall_status"], "passed", errors, "validation_summary")
        require(validation_summary, ["failed_phase_count"], 0, errors, "validation_summary")
        require(validation_summary, ["python_version"], EXPECTED_PYTHON_VERSION, errors, "validation_summary")
        require(validation_summary, ["capabilities", "toolathlon_profile"], EXPECTED_TOOLATHLON_PROFILE, errors, "validation_summary")
        smoke_targets = validation_summary.get("smoke_targets")
        if smoke_targets is not None:
            require_sequence(smoke_targets, EXPECTED_SMOKE_TARGETS, errors, "validation_summary:smoke_targets")
        excluded_targets = validation_summary.get("excluded_smoke_targets")
        if excluded_targets is not None and "google_calendar" not in excluded_targets:
            errors.append("validation_summary:excluded_smoke_targets must include 'google_calendar'")
        full_validated = validation_summary.get("full_toolathlon_profile_validated")
        if full_validated is not None and full_validated != EXPECTED_FULL_PROFILE_VALIDATED:
            errors.append(
                "validation_summary:full_toolathlon_profile_validated expected "
                f"{EXPECTED_FULL_PROFILE_VALIDATED!r}, got {full_validated!r}"
            )

    artifact_summary = read_json("release_artifacts/toolathlon_artifact_build_summary.json")
    if artifact_summary is not None:
        require(artifact_summary, ["profile"], EXPECTED_TOOLATHLON_PROFILE, errors, "toolathlon_artifact_build_summary")
        require(artifact_summary, ["overall_status"], "passed", errors, "toolathlon_artifact_build_summary")
        require(artifact_summary, ["expected_package_count"], EXPECTED_MCP_PACKAGE_COUNT, errors, "toolathlon_artifact_build_summary")
        require(artifact_summary, ["package_count"], EXPECTED_MCP_PACKAGE_COUNT, errors, "toolathlon_artifact_build_summary")
        require(artifact_summary, ["passed_count"], EXPECTED_MCP_PACKAGE_COUNT, errors, "toolathlon_artifact_build_summary")
        require(artifact_summary, ["failed_count"], 0, errors, "toolathlon_artifact_build_summary")
        packages = [item.get("package") for item in artifact_summary.get("packages", []) if isinstance(item, dict)]
        if packages:
            require_sequence(packages, EXPECTED_SMOKE_TARGETS, errors, "toolathlon_artifact_build_summary:packages")

    smoke_summary = read_json("release_artifacts/toolathlon_mcp_smoke_summary.json")
    if smoke_summary is not None:
        require(smoke_summary, ["profile"], EXPECTED_TOOLATHLON_PROFILE, errors, "toolathlon_mcp_smoke_summary")
        require(smoke_summary, ["overall_status"], "passed", errors, "toolathlon_mcp_smoke_summary")
        require(smoke_summary, ["target_count"], EXPECTED_MCP_PACKAGE_COUNT, errors, "toolathlon_mcp_smoke_summary")
        require(smoke_summary, ["passed_count"], EXPECTED_MCP_PACKAGE_COUNT, errors, "toolathlon_mcp_smoke_summary")
        require(smoke_summary, ["failed_count"], 0, errors, "toolathlon_mcp_smoke_summary")
        targets = [item.get("target") for item in smoke_summary.get("results", []) if isinstance(item, dict)]
        if targets:
            require_sequence(targets, EXPECTED_SMOKE_TARGETS, errors, "toolathlon_mcp_smoke_summary:targets")

    preflight_summary = read_json("release_artifacts/toolathlon_preflight_summary.json")
    if preflight_summary is not None:
        require(preflight_summary, ["profile"], EXPECTED_TOOLATHLON_PROFILE, errors, "toolathlon_preflight_summary")
        require(preflight_summary, ["status"], "passed", errors, "toolathlon_preflight_summary")
        require(preflight_summary, ["found_count"], EXPECTED_MCP_PACKAGE_COUNT, errors, "toolathlon_preflight_summary")
        require(preflight_summary, ["missing_count"], 0, errors, "toolathlon_preflight_summary")
        found_servers = [item.get("server") for item in preflight_summary.get("found", []) if isinstance(item, dict)]
        if found_servers:
            require_sequence(found_servers, EXPECTED_SMOKE_TARGETS, errors, "toolathlon_preflight_summary:found_servers")

    docker_smoke = read_json("release_artifacts/docker_mcp_smoke_summary.json")
    if docker_smoke is not None:
        require(docker_smoke, ["profile"], EXPECTED_TOOLATHLON_PROFILE, errors, "docker_mcp_smoke_summary")
        require(docker_smoke, ["overall_status"], "passed", errors, "docker_mcp_smoke_summary")
        require(docker_smoke, ["target_count"], EXPECTED_MCP_PACKAGE_COUNT, errors, "docker_mcp_smoke_summary")
        require(docker_smoke, ["passed_count"], EXPECTED_MCP_PACKAGE_COUNT, errors, "docker_mcp_smoke_summary")
        require(docker_smoke, ["failed_count"], 0, errors, "docker_mcp_smoke_summary")
        docker_targets = [item.get("target") for item in docker_smoke.get("results", []) if isinstance(item, dict)]
        if docker_targets:
            require_sequence(docker_targets, EXPECTED_SMOKE_TARGETS, errors, "docker_mcp_smoke_summary:targets")

    docker_preflight = read_json("release_artifacts/docker_preflight_summary.json")
    if docker_preflight is not None:
        require(docker_preflight, ["profile"], EXPECTED_TOOLATHLON_PROFILE, errors, "docker_preflight_summary")
        require(docker_preflight, ["status"], "passed", errors, "docker_preflight_summary")
        require(docker_preflight, ["missing_count"], 0, errors, "docker_preflight_summary")
        docker_found = [item.get("server") for item in docker_preflight.get("found", []) if isinstance(item, dict)]
        if docker_found:
            require_sequence(docker_found, EXPECTED_SMOKE_TARGETS, errors, "docker_preflight_summary:found_servers")

    manifest = read_json("release_artifacts/RELEASE_EVIDENCE_MANIFEST_2026-05-22.json")
    if manifest is not None:
      release_name = manifest.get("release_zip") or get_in(manifest, ["archive", "path"])
      if release_name != EXPECTED_RELEASE_NAME:
        errors.append(
          "release_evidence_manifest:release_zip/archive.path expected "
          f"{EXPECTED_RELEASE_NAME!r}, got {release_name!r}"
        )

      release_sha = (
        manifest.get("release_zip_sha256")
        or manifest.get("archive_sha256")
        or get_in(manifest, ["archive", "sha256"])
      )
      if release_sha != EXPECTED_RELEASE_SHA:
        errors.append(
          "release_evidence_manifest:release_zip_sha256/archive_sha256/archive.sha256 expected "
          f"{EXPECTED_RELEASE_SHA!r}, got {release_sha!r}"
        )

      evidence_name = manifest.get("evidence_zip")
      if evidence_name is not None and evidence_name != EXPECTED_EVIDENCE_NAME:
        errors.append(
          "release_evidence_manifest:evidence_zip expected "
          f"{EXPECTED_EVIDENCE_NAME!r}, got {evidence_name!r}"
        )

      evidence_sha = manifest.get("evidence_zip_sha256")
      if evidence_sha is not None and evidence_sha != EXPECTED_EVIDENCE_SHA:
        errors.append(
          "release_evidence_manifest:evidence_zip_sha256 expected "
          f"{EXPECTED_EVIDENCE_SHA!r}, got {evidence_sha!r}"
        )

      validated_scope = manifest.get("validated_scope")
      expected_scope = ["ToolForge", "Agent Skills", f"Toolathlon {EXPECTED_TOOLATHLON_PROFILE} profile"]
      if validated_scope is not None and validated_scope != expected_scope:
        errors.append(
          "release_evidence_manifest:validated_scope expected "
          f"{expected_scope!r}, "
          f"got {validated_scope!r}"
        )

      not_release_validated = manifest.get("not_release_validated")
      if not_release_validated is not None and (
        not isinstance(not_release_validated, list)
        or "full mcp server set" not in [s.lower() for s in not_release_validated if isinstance(s, str)]
      ):
        errors.append(
          "release_evidence_manifest:not_release_validated must be a list including 'full MCP server set'"
        )

      # Cross-file consistency checks (only when all relevant summaries parsed successfully).
      if (
        validation_summary is not None
        and artifact_summary is not None
        and smoke_summary is not None
        and preflight_summary is not None
        and docker_smoke is not None
        and docker_preflight is not None
      ):
        expected_packages = get_in(artifact_summary, ["expected_package_count"])
        found_toolathlon = get_in(preflight_summary, ["found_count"])
        target_toolathlon = get_in(smoke_summary, ["target_count"])
        found_docker = get_in(docker_preflight, ["found_count"])
        target_docker = get_in(docker_smoke, ["target_count"])

        counts = {
          "artifact.expected_package_count": expected_packages,
          "toolathlon_preflight.found_count": found_toolathlon,
          "toolathlon_smoke.target_count": target_toolathlon,
          "docker_preflight.found_count": found_docker,
          "docker_smoke.target_count": target_docker,
        }
        unique_counts = {v for v in counts.values() if isinstance(v, int)}
        if len(unique_counts) != 1:
          errors.append(
            "cross_summary_count_mismatch: "
            + ", ".join(f"{k}={v!r}" for k, v in counts.items())
          )

        cap_profile = get_in(validation_summary, ["capabilities", "toolathlon_profile"])
        profile_values = {
          "validation_summary.capabilities.toolathlon_profile": cap_profile,
          "toolathlon_artifact_build_summary.profile": get_in(artifact_summary, ["profile"]),
          "toolathlon_mcp_smoke_summary.profile": get_in(smoke_summary, ["profile"]),
          "toolathlon_preflight_summary.profile": get_in(preflight_summary, ["profile"]),
          "docker_mcp_smoke_summary.profile": get_in(docker_smoke, ["profile"]),
          "docker_preflight_summary.profile": get_in(docker_preflight, ["profile"]),
        }
        if any(v != EXPECTED_TOOLATHLON_PROFILE for v in profile_values.values()):
          errors.append(
            "cross_summary_profile_mismatch: "
            + ", ".join(f"{k}={v!r}" for k, v in profile_values.items())
          )

        require_recent_iso8601(
          get_in(manifest or {}, ["generated_at_utc"]),
          errors,
          "release_evidence_manifest:generated_at_utc",
        )
        require_recent_iso8601(
          get_in(smoke_summary, ["checked_at"]),
          errors,
          "toolathlon_mcp_smoke_summary:checked_at",
        )
        require_recent_iso8601(
          get_in(preflight_summary, ["checked_at"]),
          errors,
          "toolathlon_preflight_summary:checked_at",
        )
        require_recent_iso8601(
          get_in(docker_smoke, ["checked_at"]),
          errors,
          "docker_mcp_smoke_summary:checked_at",
        )
        require_recent_iso8601(
          get_in(docker_preflight, ["checked_at"]),
          errors,
          "docker_preflight_summary:checked_at",
        )

if errors:
    print("Evidence bundle policy check failed.", file=sys.stderr)
    for error in errors:
        print(f"- {error}", file=sys.stderr)
    raise SystemExit(1)

print("Evidence bundle policy check passed.")
PYEOF
