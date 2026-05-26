#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

FORBIDDEN_POLICY_FILE="$SCRIPT_DIR/release_forbidden_entries.sh"
if [ ! -f "$FORBIDDEN_POLICY_FILE" ]; then
  echo "Error: forbidden-entry policy file missing: $FORBIDDEN_POLICY_FILE" >&2
  exit 1
fi
# shellcheck disable=SC1090
source "$FORBIDDEN_POLICY_FILE"

SKIP_TESTS=0
SKIP_REMOTE=0
ALLOW_DIRTY=0

usage() {
  cat <<'USAGE'
Usage: bash scripts/verify_skillforge_baseline_gate.sh [--skip-tests] [--skip-remote] [--allow-dirty]

Verifies the SkillForge baseline acceptance gates:
  1) Required product/release paths exist
  2) Local main and origin/main are aligned (unless --skip-remote)
  3) Candidate zip hash matches release summary
  4) Candidate zip has no forbidden metadata/cache entries
  5) SkillForge regression gate tests pass (unless --skip-tests)
USAGE
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --skip-tests)
      SKIP_TESTS=1
      shift
      ;;
    --skip-remote)
      SKIP_REMOTE=1
      shift
      ;;
    --allow-dirty)
      ALLOW_DIRTY=1
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

required_paths=(
  "ToolForge/skillforge_ai"
  "ToolForge/tests/test_skillforge_ai"
  "ToolForge/apps/cli/skillforge_cli/main.py"
  "release_artifacts"
  "RELEASE_ATTESTATION_2026-05-22.md"
  "scripts/classify_release_upload.sh"
  "scripts/finalize_release_distribution.sh"
  "scripts/verify_release_pair.sh"
  "scripts/verify_release_gate_policy.sh"
  "scripts/verify_skip_existing_artifacts_strict.sh"
  "toolathlon-gym-curated/profiles/smoke"
  "toolathlon-gym-curated/profiles/full"
)

echo "== SkillForge Baseline Gate =="
echo "Repository: $REPO_ROOT"

missing=0
for p in "${required_paths[@]}"; do
  if [ ! -e "$REPO_ROOT/$p" ]; then
    echo "MISSING: $p" >&2
    missing=1
  fi
done
if [ "$missing" -ne 0 ]; then
  echo "Gate failed: missing required baseline paths." >&2
  exit 1
fi

echo "Path gate: passed"

if [ "$SKIP_REMOTE" -eq 0 ]; then
  local_branch="$(cd "$REPO_ROOT" && git rev-parse --abbrev-ref HEAD)"
  if [ "$local_branch" != "main" ]; then
    echo "Gate failed: current branch is '$local_branch' (expected 'main')." >&2
    exit 1
  fi

  local_sha="$(cd "$REPO_ROOT" && git rev-parse HEAD)"
  remote_sha="$(cd "$REPO_ROOT" && git ls-remote --heads origin main | awk '{print $1}')"

  if [ -z "$remote_sha" ]; then
    echo "Gate failed: could not resolve origin/main." >&2
    exit 1
  fi

  if [ "$local_sha" != "$remote_sha" ]; then
    echo "Gate failed: local main ($local_sha) != origin/main ($remote_sha)." >&2
    exit 1
  fi

  if [ "$ALLOW_DIRTY" -eq 0 ] && [ -n "$(cd "$REPO_ROOT" && git status --short)" ]; then
    echo "Gate failed: working tree is dirty." >&2
    exit 1
  fi

  echo "Git parity gate: passed"
else
  echo "Git parity gate: skipped"
fi

summary_json="$REPO_ROOT/release_artifacts/skillforge_ai_candidate_build_summary.json"
zip_path_rel="$(python3 - <<'PY' "$summary_json"
import json, sys
with open(sys.argv[1], 'r', encoding='utf-8') as f:
    data = json.load(f)
print(data['output']['path'])
PY
)"
expected_sha="$(python3 - <<'PY' "$summary_json"
import json, sys
with open(sys.argv[1], 'r', encoding='utf-8') as f:
    data = json.load(f)
print(data['output']['sha256'])
PY
)"

zip_path="$REPO_ROOT/$zip_path_rel"
if [ ! -f "$zip_path" ]; then
  echo "Gate failed: candidate zip missing at $zip_path_rel" >&2
  exit 1
fi

actual_sha="$(shasum -a 256 "$zip_path" | awk '{print $1}')"
if [ "$actual_sha" != "$expected_sha" ]; then
  echo "Gate failed: candidate zip hash mismatch." >&2
  echo "Expected: $expected_sha" >&2
  echo "Actual:   $actual_sha" >&2
  exit 1
fi

echo "Candidate hash gate: passed"

forbidden="$(zipinfo -1 "$zip_path" | grep -E "$RELEASE_FORBIDDEN_ENTRY_REGEX" || true)"
if [ -n "$forbidden" ]; then
  echo "Gate failed: forbidden entries found in candidate zip." >&2
  echo "$forbidden" >&2
  exit 1
fi

echo "Candidate hygiene gate: passed"

if [ "$SKIP_TESTS" -eq 0 ]; then
  (
    cd "$REPO_ROOT/ToolForge"
    PYTHONPATH=. pytest -q \
      tests/test_skillforge_ai/test_skill_builder.py \
      tests/test_skillforge_ai/test_validation_runner.py \
      tests/test_skillforge_ai/test_run_command.py \
      tests/test_skillforge_ai/test_mvp_skill_bundles.py \
      tests/test_tool_spec.py
  )
  echo "Regression test gate: passed"
else
  echo "Regression test gate: skipped"
fi

echo "All SkillForge baseline gates passed."
