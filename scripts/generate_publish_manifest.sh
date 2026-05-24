#!/usr/bin/env bash
# Generate a concise publish manifest for the canonical attested release pair.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

EXPECTED_RELEASE_NAME="agent_eval_skills_merged_clean-pruned-smoke.zip"
EXPECTED_RELEASE_SHA="74b34edf25141c8f96bbf03975ed8e6675dd3f574d962be2921278295544b189"
EXPECTED_EVIDENCE_NAME="agent_eval_skills_merged_clean-smoke-evidence-2026-05-22.zip"
EXPECTED_EVIDENCE_SHA="5d2e43a0d6e961f99209fab0c55e3c11c5795228200974315f44bdb5e608426c"

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
generated_utc="$(date -u '+%Y-%m-%dT%H:%M:%SZ')"

cat >"$OUTPUT_PATH" <<EOF
# Publish Manifest: Canonical Attested Pair

Generated UTC: $generated_utc

## Classification

agent_eval_skills_merged_clean - pruned smoke release candidate for controlled testing

## Approved Artifacts

Release ZIP:
- Name: $release_name
- SHA256: $EXPECTED_RELEASE_SHA

Evidence ZIP:
- Name: $evidence_name
- SHA256: $EXPECTED_EVIDENCE_SHA

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
