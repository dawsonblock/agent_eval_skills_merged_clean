#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_DIR="$ROOT_DIR/release_artifacts/validation_logs"

mkdir -p "$LOG_DIR"

cd "$ROOT_DIR"
echo "Python: $(python --version)"
echo "Node: $(node --version)"
echo "npm: $(npm --version)"
python --version > "$LOG_DIR/environment.txt"
node --version >> "$LOG_DIR/environment.txt"
npm --version >> "$LOG_DIR/environment.txt"

# Step 1: Ensure the canonical release ZIP exists before anything else.
CANONICAL_RELEASE="$ROOT_DIR/release_artifacts/agent_eval_skills_merged_clean-pruned-smoke.zip"
if [ ! -f "$CANONICAL_RELEASE" ]; then
    echo "Canonical release ZIP missing; building..."
    python scripts/build_pruned_smoke_release.py
fi

echo "Collecting smoke evidence and building evidence ZIP..."
bash "$ROOT_DIR/scripts/collect_smoke_evidence.sh"

echo "Running canonical release/evidence pair verification..."
python "$ROOT_DIR/scripts/verify_release_pair.py" | tee "$LOG_DIR/release_pair_verification.txt"

python "$ROOT_DIR/scripts/write_validation_summary.py" \
    --logs-dir "$LOG_DIR" \
    --out "$LOG_DIR/validation_summary.json"

python "$ROOT_DIR/scripts/build_evidence_zip.py" \
    --logs "$LOG_DIR"

# Step 5: Run root tests last — they require the canonical release ZIP and
# evidence to already exist so all archive/hash assertions can pass.
echo "Running root tests..."
cd "$ROOT_DIR"
pytest -q tests | tee "$LOG_DIR/test_results_root.txt"

echo "PASS: release smoke validation complete"