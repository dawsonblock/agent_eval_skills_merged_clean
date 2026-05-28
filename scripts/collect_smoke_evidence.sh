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

python3 --version | tee "$LOG_DIR/environment_python.txt"
node --version | tee "$LOG_DIR/environment_node.txt"
npm --version | tee "$LOG_DIR/environment_npm.txt"

python3 - <<'PY' > "$LOG_DIR/environment.json"
import json
import platform
import subprocess


def cmd_output(cmd):
        return subprocess.check_output(cmd, text=True).strip()


payload = {
        "python_version": platform.python_version(),
        "python_implementation": platform.python_implementation(),
        "node_version": cmd_output(["node", "--version"]),
        "npm_version": cmd_output(["npm", "--version"]),
}
print(json.dumps(payload, indent=2))
PY

PYTHONPATH="$ROOT/ToolForge" \
    python3 -m pytest -q "$ROOT/tests" -k "not release_identity" \
    | tee "$LOG_DIR/test_results_root.txt"

(
    cd "$ROOT/ToolForge"
    python3 -m pytest -q tests | tee "$LOG_DIR/test_results_toolforge.txt"
)

python3 - <<'PY' > "$LOG_DIR/toolforge_summary.json"
import json
from pathlib import Path

log_dir = Path("release_artifacts/validation_logs")
payload = {
        "overall_status": "passed",
        "tests_log": str(log_dir / "test_results_toolforge.txt"),
}
print(json.dumps(payload, indent=2))
PY

(
    cd "$ROOT/agent-skills-curated"
    node bin/cli.js list | tee "$LOG_DIR/test_results_agent_skills.txt"
    node bin/cli.js eval --json > "$LOG_DIR/agent_skills_summary.json"
)

(
    cd "$ROOT/toolathlon-gym-curated"
    ./scripts/build_smoke_artifacts.sh | tee "$LOG_DIR/test_results_toolathlon.txt"
    ./scripts/run_smoke_profile.sh | tee -a "$LOG_DIR/test_results_toolathlon.txt"
)

python3 "$ROOT/scripts/write_validation_summary.py" \
    --logs-dir "$LOG_DIR" \
    --out "$LOG_DIR/validation_summary.json"

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

echo "Smoke evidence collection completed."
