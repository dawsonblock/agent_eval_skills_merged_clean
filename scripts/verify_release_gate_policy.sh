#!/usr/bin/env bash
# shellcheck shell=bash disable=SC2250,SC2292
# trunk-ignore-all(shellcheck)
# Verify release gate check names stay consistent across workflows and docs.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

usage() {
  cat <<'USAGE'
Usage: bash scripts/verify_release_gate_policy.sh

Fails if required release-gate check names drift between workflows and docs.
USAGE
}

if [ "${1:-}" = "-h" ] || [ "${1:-}" = "--help" ]; then
  usage
  exit 0
fi

required_strings=(
  "Validate Workspace / Unified Workspace Validation"
  "Validate Workspace / Verify Canonical Attested Pair"
  "Validate Workspace / Classify Uploaded Release Artifact"
  "Release Attested Pair Gate / Verify Canonical Attested Pair"
  "Release Upload Triage / Classify Uploaded Release Artifact"
)

expected_release_zip="agent_eval_skills_merged_clean-pruned-smoke.zip"
expected_evidence_zip="agent_eval_skills_merged_clean-smoke-evidence-2026-05-22.zip"

declare -a files=(
  "$REPO_ROOT/.github/workflows/validate.yml"
  "$REPO_ROOT/.github/workflows/release-attested-gate.yml"
  "$REPO_ROOT/.github/workflows/release-upload-triage.yml"
  "$REPO_ROOT/README.md"
  "$REPO_ROOT/DEPLOYMENT.md"
  "$REPO_ROOT/RELEASE_GATE_RUNBOOK.md"
  "$REPO_ROOT/scripts/operator_release_gate_check.sh"
  "$REPO_ROOT/scripts/operator_release_upload_triage.sh"
)

missing=0

for f in "${files[@]}"; do
  if [ ! -f "$f" ]; then
    echo "Missing required file: $f" >&2
    missing=1
  fi
done

if [ "$missing" -ne 0 ]; then
  exit 1
fi

for s in "${required_strings[@]}"; do
  if ! grep -Fq "$s" "$REPO_ROOT/README.md" \
      && ! grep -Fq "$s" "$REPO_ROOT/DEPLOYMENT.md" \
      && ! grep -Fq "$s" "$REPO_ROOT/RELEASE_GATE_RUNBOOK.md" \
      && ! grep -Fq "$s" "$REPO_ROOT/scripts/operator_release_gate_check.sh" \
      && ! grep -Fq "$s" "$REPO_ROOT/scripts/operator_release_upload_triage.sh"; then
    echo "Required check name missing from all docs/helpers: $s" >&2
    missing=1
  fi
done

if ! grep -Fq "name: Validate Workspace" "$REPO_ROOT/.github/workflows/validate.yml"; then
  echo "validate.yml missing expected workflow name." >&2
  missing=1
fi

if ! grep -Fq "name: Verify Canonical Attested Pair" "$REPO_ROOT/.github/workflows/validate.yml"; then
  echo "validate.yml missing job name: Verify Canonical Attested Pair" >&2
  missing=1
fi

if ! grep -Fq "name: Classify Uploaded Release Artifact" "$REPO_ROOT/.github/workflows/validate.yml"; then
  echo "validate.yml missing job name: Classify Uploaded Release Artifact" >&2
  missing=1
fi

if ! grep -Fq "name: Release Attested Pair Gate" "$REPO_ROOT/.github/workflows/release-attested-gate.yml"; then
  echo "release-attested-gate.yml missing expected workflow name." >&2
  missing=1
fi

if ! grep -Fq "name: Verify Canonical Attested Pair" "$REPO_ROOT/.github/workflows/release-attested-gate.yml"; then
  echo "release-attested-gate.yml missing expected job name." >&2
  missing=1
fi

if ! grep -Fq "name: Release Upload Triage" "$REPO_ROOT/.github/workflows/release-upload-triage.yml"; then
  echo "release-upload-triage.yml missing expected workflow name." >&2
  missing=1
fi

if ! grep -Fq "name: Classify Uploaded Release Artifact" "$REPO_ROOT/.github/workflows/release-upload-triage.yml"; then
  echo "release-upload-triage.yml missing expected job name." >&2
  missing=1
fi

if ! grep -Fq "RELEASE_ZIP_PATH: $expected_release_zip" "$REPO_ROOT/.github/workflows/validate.yml"; then
  echo "validate.yml missing canonical release zip path: $expected_release_zip" >&2
  missing=1
fi

if ! grep -Fq "EVIDENCE_ZIP_PATH: $expected_evidence_zip" "$REPO_ROOT/.github/workflows/validate.yml"; then
  echo "validate.yml missing canonical evidence zip path: $expected_evidence_zip" >&2
  missing=1
fi

if ! grep -Fq "RELEASE_ZIP_PATH: $expected_release_zip" "$REPO_ROOT/.github/workflows/release-attested-gate.yml"; then
  echo "release-attested-gate.yml missing canonical release zip path: $expected_release_zip" >&2
  missing=1
fi

if ! grep -Fq "EVIDENCE_ZIP_PATH: $expected_evidence_zip" "$REPO_ROOT/.github/workflows/release-attested-gate.yml"; then
  echo "release-attested-gate.yml missing canonical evidence zip path: $expected_evidence_zip" >&2
  missing=1
fi

if [ "$missing" -ne 0 ]; then
  echo "Release gate policy consistency check failed." >&2
  exit 1
fi

echo "Release gate policy consistency check passed."