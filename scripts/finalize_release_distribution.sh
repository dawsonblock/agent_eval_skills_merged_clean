#!/usr/bin/env bash
# Final release-distribution gate for pruned smoke release candidate.
#
# This script enforces:
# - exact canonical release/evidence filenames + SHA256 values
# - clean release ZIP hygiene
# - evidence bundle required files + required values
# - canonical pair verification via existing policy scripts

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

EXPECTED_RELEASE_NAME="agent_eval_skills_merged_clean-pruned-smoke.zip"
EXPECTED_RELEASE_SHA="74b34edf25141c8f96bbf03975ed8e6675dd3f574d962be2921278295544b189"
EXPECTED_EVIDENCE_NAME="agent_eval_skills_merged_clean-smoke-evidence-2026-05-22.zip"
EXPECTED_EVIDENCE_SHA="5d2e43a0d6e961f99209fab0c55e3c11c5795228200974315f44bdb5e608426c"

RELEASE_PATH="${RELEASE_ZIP_PATH:-$REPO_ROOT/$EXPECTED_RELEASE_NAME}"
EVIDENCE_PATH="${EVIDENCE_ZIP_PATH:-$REPO_ROOT/$EXPECTED_EVIDENCE_NAME}"

usage() {
  cat <<'USAGE'
Usage: bash scripts/finalize_release_distribution.sh [--release PATH] [--evidence PATH]

Runs final release distribution checks for the canonical smoke pair.

Options:
  --release PATH   Path to release ZIP (default: canonical repo-root file)
  --evidence PATH  Path to evidence ZIP (default: canonical repo-root file)
  -h, --help       Show this help

Environment overrides:
  RELEASE_ZIP_PATH
  EVIDENCE_ZIP_PATH

Exit codes:
  0 = publish-ready canonical pair
  1 = failed check or new candidate required
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
  echo "Error: shasum is required." >&2
  exit 1
fi

if ! command -v unzip >/dev/null 2>&1; then
  echo "Error: unzip is required." >&2
  exit 1
fi

if [ ! -f "$RELEASE_PATH" ]; then
  echo "Error: release ZIP not found: $RELEASE_PATH" >&2
  exit 1
fi

if [ ! -f "$EVIDENCE_PATH" ]; then
  echo "Error: evidence ZIP not found: $EVIDENCE_PATH" >&2
  exit 1
fi

release_name="$(basename "$RELEASE_PATH")"
evidence_name="$(basename "$EVIDENCE_PATH")"
release_sha="$(shasum -a 256 "$RELEASE_PATH" | awk '{print $1}')"
evidence_sha="$(shasum -a 256 "$EVIDENCE_PATH" | awk '{print $1}')"

if [ "$release_name" != "$EXPECTED_RELEASE_NAME" ]; then
  echo "Release filename mismatch: expected $EXPECTED_RELEASE_NAME, got $release_name" >&2
  exit 1
fi

if [ "$evidence_name" != "$EXPECTED_EVIDENCE_NAME" ]; then
  echo "Evidence filename mismatch: expected $EXPECTED_EVIDENCE_NAME, got $evidence_name" >&2
  exit 1
fi

if [ "$release_sha" != "$EXPECTED_RELEASE_SHA" ]; then
  cat >&2 <<EOF
Release ZIP hash differs from canonical attestation.
Expected: $EXPECTED_RELEASE_SHA
Actual:   $release_sha
Treat this as a new candidate and re-run full validation + new evidence + new attestation.
EOF
  exit 1
fi

if [ "$evidence_sha" != "$EXPECTED_EVIDENCE_SHA" ]; then
  cat >&2 <<EOF
Evidence ZIP hash differs from canonical attestation.
Expected: $EXPECTED_EVIDENCE_SHA
Actual:   $evidence_sha
Treat this as a new candidate and regenerate evidence + attestation.
EOF
  exit 1
fi

# Phase: release ZIP hygiene gate.
if unzip -l "$RELEASE_PATH" | grep -E "__MACOSX|/\._|\.DS_Store|node_modules|\.validation_logs|__pycache__|\.pytest_cache|\.mypy_cache|\.ruff_cache|\.venv" >/dev/null; then
  echo "Release ZIP hygiene check failed: forbidden entries found." >&2
  unzip -l "$RELEASE_PATH" | grep -E "__MACOSX|/\._|\.DS_Store|node_modules|\.validation_logs|__pycache__|\.pytest_cache|\.mypy_cache|\.ruff_cache|\.venv" >&2
  exit 1
fi

# Use existing policy scripts for evidence and pair checks.
(cd "$REPO_ROOT" && bash scripts/verify_evidence_bundle.sh --evidence "$EVIDENCE_PATH")
(cd "$REPO_ROOT" && bash scripts/verify_release_pair.sh --release "$RELEASE_PATH" --evidence "$EVIDENCE_PATH")
(cd "$REPO_ROOT" && bash scripts/verify_release_gate_policy.sh)

cat <<EOF

Publish-ready canonical pair verified.

Release ZIP:
$release_name
SHA256: $release_sha

Evidence ZIP:
$evidence_name
SHA256: $evidence_sha

Publish note:
agent_eval_skills_merged_clean is a pruned smoke release candidate for controlled testing.
Validated scope:
- ToolForge
- Agent Skills
- Toolathlon smoke profile
Retained but not release-validated:
- Full Toolathlon profile
- all task material
- full MCP server set
This is not production-grade.
This is not hostile-code-safe.
Use disposable benchmark containers.
Run dependency/security audit before broader deployment.
EOF
