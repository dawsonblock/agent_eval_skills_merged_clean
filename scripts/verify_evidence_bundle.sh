#!/usr/bin/env bash
# shellcheck shell=bash disable=SC2250,SC2292
# trunk-ignore-all(shellcheck)
# Verify evidence ZIP contains required files and required smoke-profile values.

set -euo pipefail

EVIDENCE_PATH="${EVIDENCE_ZIP_PATH:-}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"


# Use evidence bundle policy for forbidden entries
FORBIDDEN_POLICY_FILE="$SCRIPT_DIR/release_forbidden_entries.sh"
if [ ! -f "$FORBIDDEN_POLICY_FILE" ]; then
  echo "Error: forbidden-entry policy file missing: $FORBIDDEN_POLICY_FILE" >&2
  exit 1
fi
# shellcheck disable=SC1090
EVIDENCE_BUNDLE=1 source "$FORBIDDEN_POLICY_FILE"

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
    ".validation_logs/validation_summary.json",
    ".validation_logs/toolathlon_build_smoke_summary.json",
    ".validation_logs/toolathlon_smoke_summary.json",
    ".validation_logs/toolathlon_preflight_smoke_summary.json",
    ".validation_logs/release_hashes.json",
    ".validation_logs/secrets_scan.txt",
    ".validation_logs/environment.json",
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

    validation_summary = read_json(".validation_logs/validation_summary.json")
    if validation_summary is not None:
        require(validation_summary, ["profile"], EXPECTED_TOOLATHLON_PROFILE, errors, "validation_summary")
        status = validation_summary.get("status")
        if status != "pass" and status != "passed":
            errors.append(f"validation_summary:status expected 'pass' or 'passed', got {status!r}")
        require(validation_summary, ["capabilities", "toolathlon_profile"], EXPECTED_TOOLATHLON_PROFILE, errors, "validation_summary")
        components = validation_summary.get("components", {})
        toolathlon = components.get("toolathlon_smoke")
        if toolathlon is not None and toolathlon != "pass":
            errors.append(f"validation_summary:components.toolathlon_smoke expected 'pass', got {toolathlon!r}")

    artifact_summary = read_json(".validation_logs/toolathlon_build_smoke_summary.json")
    if artifact_summary is not None:
        require(artifact_summary, ["profile"], EXPECTED_TOOLATHLON_PROFILE, errors, "toolathlon_build_smoke_summary")
        servers = artifact_summary.get("servers", {})
        for target_name in EXPECTED_SMOKE_TARGETS:
            srv = servers.get(target_name)
            if srv is None:
                errors.append(f"toolathlon_build_smoke_summary: missing server '{target_name}'")
            elif srv.get("build") != "pass":
                errors.append(f"toolathlon_build_smoke_summary:{target_name}.build expected 'pass', got {srv.get('build')!r}")

    smoke_summary = read_json(".validation_logs/toolathlon_smoke_summary.json")
    if smoke_summary is not None:
        require(smoke_summary, ["profile"], EXPECTED_TOOLATHLON_PROFILE, errors, "toolathlon_smoke_summary")
        require(smoke_summary, ["overall_status"], "passed", errors, "toolathlon_smoke_summary")
        require(smoke_summary, ["failed_count"], 0, errors, "toolathlon_smoke_summary")
        targets = [item.get("target") for item in smoke_summary.get("results", []) if isinstance(item, dict)]
        if targets:
            require_sequence(targets, EXPECTED_SMOKE_TARGETS, errors, "toolathlon_smoke_summary:targets")

    preflight_summary = read_json(".validation_logs/toolathlon_preflight_smoke_summary.json")
    if preflight_summary is not None:
        require(preflight_summary, ["profile"], EXPECTED_TOOLATHLON_PROFILE, errors, "toolathlon_preflight_smoke_summary")
        require(preflight_summary, ["status"], "passed", errors, "toolathlon_preflight_smoke_summary")
        require(preflight_summary, ["found_count"], EXPECTED_MCP_PACKAGE_COUNT, errors, "toolathlon_preflight_smoke_summary")
        require(preflight_summary, ["missing_count"], 0, errors, "toolathlon_preflight_smoke_summary")
        found_servers = [item.get("server") for item in preflight_summary.get("found", []) if isinstance(item, dict)]
        if found_servers:
            require_sequence(found_servers, EXPECTED_SMOKE_TARGETS, errors, "toolathlon_preflight_smoke_summary:found_servers")

    release_hashes = read_json(".validation_logs/release_hashes.json")
    if release_hashes is not None:
        rh_release = release_hashes.get("release_sha256")
        if rh_release and rh_release != EXPECTED_RELEASE_SHA:
            errors.append(f"release_hashes.json:release_sha256 expected {EXPECTED_RELEASE_SHA!r}, got {rh_release!r}")
        rh_profile = release_hashes.get("profile")
        if rh_profile and rh_profile != EXPECTED_TOOLATHLON_PROFILE:
            errors.append(f"release_hashes.json:profile expected {EXPECTED_TOOLATHLON_PROFILE!r}, got {rh_profile!r}")

if errors:
    print("Evidence bundle policy check failed.", file=sys.stderr)
    for error in errors:
        print(f"- {error}", file=sys.stderr)
    raise SystemExit(1)

print("Evidence bundle policy check passed.")
PYEOF
