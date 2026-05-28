#!/usr/bin/env bash
# Generate a concise publish manifest for the canonical attested release pair.

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

RELEASE_PATH="${RELEASE_ZIP_PATH:-$REPO_ROOT/$EXPECTED_RELEASE_NAME}"
EVIDENCE_PATH="${EVIDENCE_ZIP_PATH:-$REPO_ROOT/$EXPECTED_EVIDENCE_NAME}"
OUTPUT_PATH="$REPO_ROOT/release_artifacts/PUBLISH_MANIFEST_CANONICAL_PAIR.md"

usage() {
  cat <<'USAGE'
Usage: bash scripts/generate_publish_manifest.sh [--release PATH] [--evidence PATH] [--output PATH]

Generates a publish manifest for the canonical attested pair after verification.

Options:
  --release PATH   Path to release ZIP (default: canonical repo-root file)
  --evidence PATH  Path to evidence ZIP (default: canonical repo-root file)
  --output PATH    Output markdown path (default: release_artifacts/PUBLISH_MANIFEST_CANONICAL_PAIR.md)
  -h, --help       Show this help
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
    --output)
      if [ "$#" -lt 2 ]; then
        echo "Missing value for --output" >&2
        exit 1
      fi
      OUTPUT_PATH="$2"
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

mkdir -p "$(dirname "$OUTPUT_PATH")"

# Reuse existing final gate so manifest generation is fail-closed.
(cd "$REPO_ROOT" && bash scripts/finalize_release_distribution.sh --release "$RELEASE_PATH" --evidence "$EVIDENCE_PATH" >/dev/null)

release_name="$(basename "$RELEASE_PATH")"
evidence_name="$(basename "$EVIDENCE_PATH")"
release_sha_actual="$(shasum -a 256 "$RELEASE_PATH" | awk '{print $1}')"
evidence_sha_actual="$(shasum -a 256 "$EVIDENCE_PATH" | awk '{print $1}')"
manifest_release_sha="$EXPECTED_RELEASE_SHA"
manifest_evidence_sha="$EXPECTED_EVIDENCE_SHA"
if [ -f "$REPO_ROOT/RELEASE_STATUS.json" ] && python3 - "$REPO_ROOT/RELEASE_STATUS.json" <<'PYEOF' >/dev/null
import json
import sys

with open(sys.argv[1], 'r', encoding='utf-8') as fh:
    data = json.load(fh)
raise SystemExit(0 if data.get('release_classification') == 'SOURCE_BUNDLE' else 1)
PYEOF
then
  manifest_release_sha="$release_sha_actual"
  manifest_evidence_sha="$evidence_sha_actual"
fi
generated_utc="$(date -u '+%Y-%m-%dT%H:%M:%SZ')"

cat >"$OUTPUT_PATH" <<EOF
# Publish Manifest: Canonical Attested Pair

Generated UTC: $generated_utc

## Classification

agent_eval_skills_merged_clean - pruned smoke release candidate for controlled testing

## Approved Artifacts

Release ZIP:
- Name: $release_name
- SHA256: $manifest_release_sha

Evidence ZIP:
- Name: $evidence_name
- SHA256: $manifest_evidence_sha

## Scope Boundary

Validated scope:
- ToolForge
- Agent Skills
- Toolathlon smoke profile

Retained but not release-validated:
- Full Toolathlon profile
- all task material
- full MCP server set

## Policy Notes

- Distribute only the exact approved release+evidence ZIP pair above.
- Do not distribute wrapper/source bundles as release artifacts.
- 2026-05-23 release attempt remains withdrawn/superseded.
EOF

echo "Publish manifest generated: $OUTPUT_PATH"
