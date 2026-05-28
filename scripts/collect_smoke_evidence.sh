#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
LOG_DIR="$ROOT/release_artifacts/validation_logs"
STAMP="${RELEASE_DATE:-$(date -u +%Y-%m-%d)}"
EVIDENCE_ZIP="$ROOT/release_artifacts/agent_eval_skills_merged_clean-smoke-evidence-${STAMP}.zip"

mkdir -p "$LOG_DIR"

export TOOLATHLON_PROFILE=smoke
export ENFORCE_RC_SMOKE_PROFILE=1

python3 "$ROOT/scripts/write_validation_summary.py" --profile smoke

PYTHONPATH="$ROOT/ToolForge" python3 -m pytest -q "$ROOT/tests" | tee "$LOG_DIR/test_results_root.txt"
(
  cd "$ROOT/ToolForge"
  python3 -m pytest -q tests | tee "$LOG_DIR/test_results_toolforge.txt"
)
(
  cd "$ROOT/agent-skills-curated"
  node bin/cli.js eval --json | tee "$LOG_DIR/test_results_agent_skills.txt"
)
(
  cd "$ROOT/toolathlon-gym-curated"
  python3 scripts/smoke_mcp_servers.py --profile smoke --json-output "$LOG_DIR/toolathlon_mcp_smoke_summary.json"
) | tee "$LOG_DIR/test_results_toolathlon.txt"

python3 "$ROOT/scripts/sanitize_release_paths.py"
python3 "$ROOT/scripts/build_evidence_zip.py" \
  --logs "$LOG_DIR" \
  --out "$EVIDENCE_ZIP" \
  --release-sha "$(python3 - <<'PY'
import hashlib
from pathlib import Path
p = Path('release_artifacts/agent_eval_skills_merged_clean-pruned-smoke.zip')
if not p.exists():
    raise SystemExit('Missing release ZIP: release_artifacts/agent_eval_skills_merged_clean-pruned-smoke.zip')
h = hashlib.sha256()
with p.open('rb') as f:
    for chunk in iter(lambda: f.read(1024 * 1024), b''):
        h.update(chunk)
print(h.hexdigest())
PY
)"

python3 "$ROOT/scripts/check_release_hash_consistency.py"
python3 "$ROOT/scripts/verify_release_pair.py" \
  --release "release_artifacts/agent_eval_skills_merged_clean-pruned-smoke.zip" \
  --evidence "release_artifacts/agent_eval_skills_merged_clean-smoke-evidence-${STAMP}.zip" \
  --strict

python3 - <<'PY'
import hashlib
from pathlib import Path
p = Path('release_artifacts').glob('agent_eval_skills_merged_clean-smoke-evidence-*.zip')
latest = max(p, key=lambda x: x.stat().st_mtime)
h = hashlib.sha256()
with latest.open('rb') as f:
    for chunk in iter(lambda: f.read(1024 * 1024), b''):
        h.update(chunk)
print(f"Evidence ZIP: {latest}")
print(f"Evidence SHA256: {h.hexdigest()}")
PY
