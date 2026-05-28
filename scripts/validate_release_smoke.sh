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

echo "Running root tests..."
pytest -q tests | tee "$LOG_DIR/test_results_root.txt"

echo "Running ToolForge tests..."
cd "$ROOT_DIR/ToolForge"
python -m pytest -q | tee "$LOG_DIR/test_results_toolforge.txt"
toolforge doctor | tee "$LOG_DIR/toolforge_doctor.txt"

echo "Running Agent Skills validation..."
cd "$ROOT_DIR/agent-skills-curated"
node bin/cli.js list | tee "$LOG_DIR/agent_skills_list.txt"
node bin/cli.js eval --json > "$LOG_DIR/agent_skills_summary.json"
node scripts/validate_packages.js | tee "$LOG_DIR/agent_skill_packages.txt"

echo "Running Toolathlon smoke validation..."
cd "$ROOT_DIR/toolathlon-gym-curated"
./scripts/build_smoke_artifacts.sh | tee "$LOG_DIR/toolathlon_build_smoke.txt"
./scripts/run_smoke_profile.sh | tee "$LOG_DIR/toolathlon_smoke.txt"

echo "Running secret fixture policy check..."
cd "$ROOT_DIR"
python scripts/check_for_real_secrets.py | tee "$LOG_DIR/secrets_scan.txt"

python scripts/write_validation_summary.py
echo "PASS: release smoke validation complete"