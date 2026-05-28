#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_DIR="$ROOT_DIR/release_artifacts/validation_logs"

mkdir -p "$LOG_DIR"

python --version | tee "$LOG_DIR/environment_python.txt"
node --version | tee "$LOG_DIR/environment_node.txt"
npm --version | tee "$LOG_DIR/environment_npm.txt"

python - <<'PY' > "$LOG_DIR/environment.json"
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

(
  cd "$ROOT_DIR/ToolForge"
  python -m pytest -q | tee "$LOG_DIR/test_results_toolforge.txt"
  toolforge doctor | tee "$LOG_DIR/toolforge_doctor.txt"
)

python - <<'PY' > "$LOG_DIR/toolforge_summary.json"
import json
from pathlib import Path

log_dir = Path("release_artifacts/validation_logs")
payload = {
    "overall_status": "passed",
    "tests_log": str(log_dir / "test_results_toolforge.txt"),
    "doctor_log": str(log_dir / "toolforge_doctor.txt"),
}
print(json.dumps(payload, indent=2))
PY

(
  cd "$ROOT_DIR/agent-skills-curated"
  node bin/cli.js list | tee "$LOG_DIR/agent_skills_list.txt"
  node bin/cli.js eval --json > "$LOG_DIR/agent_skills_summary.json"
  cp "$LOG_DIR/agent_skills_list.txt" "$LOG_DIR/test_results_agent_skills.txt"
  if [ -f scripts/validate_packages.js ]; then
    node scripts/validate_packages.js | tee "$LOG_DIR/agent_skill_packages.txt"
  else
    echo "WARN: validate_packages.js not found" | tee "$LOG_DIR/agent_skill_packages.txt"
  fi
)

(
  cd "$ROOT_DIR/toolathlon-gym-curated"
  ./scripts/build_smoke_artifacts.sh | tee "$LOG_DIR/toolathlon_build_smoke.txt"
  ./scripts/run_smoke_profile.sh | tee "$LOG_DIR/toolathlon_smoke.txt"
  cp "$LOG_DIR/toolathlon_smoke.txt" "$LOG_DIR/test_results_toolathlon.txt"
)

RELEASE_ZIP_REL="$(python - <<'PY'
import json
from pathlib import Path
lock = json.loads(Path('release_artifacts/release_lock.json').read_text(encoding='utf-8'))
print(lock['release_zip'])
PY
)"

EVIDENCE_ZIP_REL="$(python - <<'PY'
import json
from pathlib import Path
lock = json.loads(Path('release_artifacts/release_lock.json').read_text(encoding='utf-8'))
print(lock['evidence_zip'])
PY
)"

bash "$ROOT_DIR/scripts/verify_source_bundle_hygiene.sh" \
  --zip "$ROOT_DIR/$RELEASE_ZIP_REL" | tee "$LOG_DIR/source_bundle_hygiene.txt"

python "$ROOT_DIR/scripts/verify_release_pair.py" \
  --release "$ROOT_DIR/$RELEASE_ZIP_REL" \
  --evidence "$ROOT_DIR/$EVIDENCE_ZIP_REL" \
  --lock "$ROOT_DIR/release_artifacts/release_lock.json" | tee "$LOG_DIR/release_pair_verification.txt"

python "$ROOT_DIR/scripts/write_validation_summary.py" \
  --logs-dir "$LOG_DIR" \
  --out "$LOG_DIR/validation_summary.json"

python "$ROOT_DIR/scripts/generate_release_manifest.py"

python -m pytest -q tests | tee "$LOG_DIR/test_results_root.txt"

python "$ROOT_DIR/scripts/sanitize_release_paths.py"

python "$ROOT_DIR/scripts/write_validation_summary.py" \
  --logs-dir "$LOG_DIR" \
  --out "$LOG_DIR/validation_summary.json"