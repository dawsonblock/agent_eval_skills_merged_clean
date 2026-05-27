#!/usr/bin/env bash
# Unified workspace validation script
# Validates ToolForge, Agent Skills, and Toolathlon components.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && cd .. && pwd)"
TOOLFORGE_DIR="$REPO_ROOT/ToolForge"
AGENT_SKILLS_DIR="$REPO_ROOT/agent-skills-curated"
TOOLATHLON_DIR="$REPO_ROOT/toolathlon-gym-curated"
RUN_INTEGRATION="${RUN_INTEGRATION:-0}"
RUN_DOCKER="${RUN_DOCKER:-0}"
DOCKER_CONTEXT="${DOCKER_CONTEXT:-default}"
TOOLATHLON_PROFILE="${TOOLATHLON_PROFILE:-smoke}"
ENFORCE_RC_SMOKE_PROFILE="${ENFORCE_RC_SMOKE_PROFILE:-0}"
export TOOLATHLON_PROFILE

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
NC='\033[0m'

failed=0
HAVE_GIT=0
INITIAL_GIT_STATUS_FILTERED=""
TOOLFORGE_PYTHON_OK=1

TOOLFORGE_STATUS="not-run"
AGENT_SKILLS_STATUS="not-run"
TOOLATHLON_STATUS="not-run"
DOCKER_STATUS="skipped"

RUN_STARTED_EPOCH="$(date +%s)"
RUN_STARTED_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

TOOLFORGE_DURATION_SECONDS=0
AGENT_SKILLS_DURATION_SECONDS=0
TOOLATHLON_DURATION_SECONDS=0
DOCKER_DURATION_SECONDS=0

LOG_DIR="$REPO_ROOT/.validation_logs"
mkdir -p "$LOG_DIR"

TOOLFORGE_PYTHON_LOG="$LOG_DIR/toolforge_python_version.log"
TOOLFORGE_INSTALL_LOG="$LOG_DIR/toolforge_install.log"
TOOLFORGE_DOCTOR_LOG="$LOG_DIR/toolforge_doctor.log"
TOOLFORGE_SCHEMA_PATH_SAFETY_LOG="$LOG_DIR/toolforge_schema_path_safety.log"
TOOLFORGE_VALIDATOR_LOG="$LOG_DIR/toolforge_validator_tests.log"
TOOLFORGE_REGISTRY_LOG="$LOG_DIR/toolforge_registry_tests.log"
TOOLFORGE_CLI_LOG="$LOG_DIR/toolforge_cli_tests.log"
TOOLFORGE_E2E_LOG="$LOG_DIR/toolforge_e2e_tests.log"
TOOLFORGE_EVAL_LOG="$LOG_DIR/toolforge_eval_tests.log"
TOOLFORGE_INTEGRATION_LOG="$LOG_DIR/toolforge_integration_tests.log"
AGENT_SKILLS_LIST_LOG="$LOG_DIR/agent_skills_list.log"
AGENT_SKILLS_EVAL_LOG="$LOG_DIR/agent_skills_eval.log"
TOOLATHLON_BUILD_LOG="$LOG_DIR/toolathlon_artifact_build.log"
TOOLATHLON_PREFLIGHT_LOG="$LOG_DIR/toolathlon_preflight.log"
TOOLATHLON_PREFLIGHT_SUMMARY_JSON="$LOG_DIR/toolathlon_preflight_summary.json"
TOOLATHLON_ARTIFACT_BUILD_SUMMARY_JSON="$LOG_DIR/toolathlon_artifact_build_summary.json"
TOOLATHLON_SMOKE_SUMMARY_JSON="$LOG_DIR/toolathlon_mcp_smoke_summary.json"
DOCKER_BUILD_LOG="$LOG_DIR/docker_build.log"
DOCKER_PREFLIGHT_LOG="$LOG_DIR/docker_preflight.log"
DOCKER_PREFLIGHT_SUMMARY_JSON="$LOG_DIR/docker_preflight_summary.json"
DOCKER_SMOKE_SUMMARY_JSON="$LOG_DIR/docker_mcp_smoke_summary.json"
VALIDATION_SUMMARY_JSON="$LOG_DIR/validation_summary.json"

# Clear logs from prior runs.
: > "$TOOLFORGE_PYTHON_LOG"
: > "$TOOLFORGE_INSTALL_LOG"
: > "$TOOLFORGE_DOCTOR_LOG"
: > "$TOOLFORGE_SCHEMA_PATH_SAFETY_LOG"
: > "$TOOLFORGE_VALIDATOR_LOG"
: > "$TOOLFORGE_REGISTRY_LOG"
: > "$TOOLFORGE_CLI_LOG"
: > "$TOOLFORGE_E2E_LOG"
: > "$TOOLFORGE_EVAL_LOG"
: > "$TOOLFORGE_INTEGRATION_LOG"
: > "$AGENT_SKILLS_LIST_LOG"
: > "$AGENT_SKILLS_EVAL_LOG"
: > "$TOOLATHLON_BUILD_LOG"
: > "$TOOLATHLON_PREFLIGHT_LOG"
: > "$DOCKER_BUILD_LOG"
: > "$DOCKER_PREFLIGHT_LOG"
rm -f "$DOCKER_PREFLIGHT_SUMMARY_JSON"
rm -f "$TOOLATHLON_SMOKE_SUMMARY_JSON" "$DOCKER_SMOKE_SUMMARY_JSON"

if git -C "$REPO_ROOT" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  HAVE_GIT=1
  INITIAL_GIT_STATUS="$(git -C "$REPO_ROOT" status --porcelain)"
  INITIAL_GIT_STATUS_FILTERED="$(printf '%s\n' "$INITIAL_GIT_STATUS" | grep -Ev '^[ MARCUD?!]{2} toolathlon-gym-curated/local_servers/.*/(build|dist|\.venv|node_modules)/' || true)"
else
  echo "⚠ Not a Git checkout; skipping dirty-tree check"
fi

echo "Workspace root: $REPO_ROOT"
echo "Log directory: $LOG_DIR"
echo "Toolathlon profile: $TOOLATHLON_PROFILE"
echo "Enforce RC smoke profile: $ENFORCE_RC_SMOKE_PROFILE"
echo

if [ "$ENFORCE_RC_SMOKE_PROFILE" = "1" ] && [ "$TOOLATHLON_PROFILE" != "smoke" ]; then
  echo -e "${RED}✗ ENFORCE_RC_SMOKE_PROFILE=1 requires TOOLATHLON_PROFILE=smoke (got '$TOOLATHLON_PROFILE')${NC}"
  exit 1
fi

run_step() {
  local label="$1"
  local timeout="$2"
  local cwd="$3"
  local log_file="$4"
  shift 4

  echo -e "${YELLOW}→ $label${NC}"
  if (cd "$cwd" && python "$REPO_ROOT/scripts/run_with_timeout.py" --timeout "$timeout" -- "$@") 2>&1 | tee "$log_file"; then
    echo "✓ $label"
    return 0
  fi

  echo -e "${RED}✗ $label failed${NC} (log: $log_file)"
  return 1
}

run_python_version_check() {
  python - <<'PY'
import sys

if sys.version_info < (3, 9):
    raise SystemExit(
        "ToolForge supports Python >=3.9,<3.13. "
        "Use Python 3.9 through 3.12 for workspace validation."
    )
if sys.version_info >= (3, 13):
    raise SystemExit(
        "ToolForge supports Python >=3.9,<3.13. "
        "Use Python 3.12 or lower for workspace validation."
    )
print(f"Python version OK for ToolForge: {sys.version.split()[0]}")
PY
}

ensure_pyyaml() {
  if python - <<'PY' >/dev/null 2>&1
import yaml  # noqa: F401
PY
  then
    return 0
  fi

  echo "PyYAML missing; installing into current environment..." | tee -a "$TOOLATHLON_PREFLIGHT_LOG"
  python -m pip install pyyaml >> "$TOOLATHLON_PREFLIGHT_LOG" 2>&1
}

status_to_exit_code() {
  case "$1" in
    passed) echo 0 ;;
    failed|unsupported-python) echo 1 ;;
    skipped|not-run) echo "" ;;
    *) echo "" ;;
  esac
}

write_validation_summary() {
  local run_finished_epoch run_finished_at run_duration
  run_finished_epoch="$(date +%s)"
  run_finished_at="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  run_duration="$((run_finished_epoch - RUN_STARTED_EPOCH))"

  local workspace_python_version workspace_python_executable
  workspace_python_version="$(python - <<'PY'
import sys
print(sys.version.split()[0])
PY
)"
  workspace_python_executable="$(python - <<'PY'
import sys
print(sys.executable)
PY
)"

  local docker_available toolforge_python_supported
  if command -v docker >/dev/null 2>&1; then
    docker_available=true
  else
    docker_available=false
  fi

  if [ "$TOOLFORGE_PYTHON_OK" -eq 1 ]; then
    toolforge_python_supported=true
  else
    toolforge_python_supported=false
  fi

  export RUN_STARTED_AT RUN_INTEGRATION RUN_DOCKER TOOLATHLON_PROFILE
  export ENFORCE_RC_SMOKE_PROFILE
  export TOOLFORGE_STATUS AGENT_SKILLS_STATUS TOOLATHLON_STATUS DOCKER_STATUS
  export TOOLFORGE_DURATION_SECONDS AGENT_SKILLS_DURATION_SECONDS
  export TOOLATHLON_DURATION_SECONDS DOCKER_DURATION_SECONDS
  export WORKSPACE_PYTHON_VERSION="$workspace_python_version"
  export WORKSPACE_PYTHON_EXECUTABLE="$workspace_python_executable"
  export TOOLFORGE_EXIT_CODE AGENT_SKILLS_EXIT_CODE TOOLATHLON_EXIT_CODE DOCKER_EXIT_CODE
  export TOOLFORGE_PYTHON_LOG TOOLFORGE_INSTALL_LOG TOOLFORGE_DOCTOR_LOG
  export TOOLFORGE_SCHEMA_PATH_SAFETY_LOG TOOLFORGE_VALIDATOR_LOG
  export TOOLFORGE_REGISTRY_LOG TOOLFORGE_CLI_LOG TOOLFORGE_E2E_LOG
  export TOOLFORGE_EVAL_LOG TOOLFORGE_INTEGRATION_LOG
  export AGENT_SKILLS_LIST_LOG AGENT_SKILLS_EVAL_LOG
  export TOOLATHLON_BUILD_LOG TOOLATHLON_PREFLIGHT_LOG TOOLATHLON_PREFLIGHT_SUMMARY_JSON
  export TOOLATHLON_ARTIFACT_BUILD_SUMMARY_JSON TOOLATHLON_SMOKE_SUMMARY_JSON
  export DOCKER_BUILD_LOG DOCKER_PREFLIGHT_LOG DOCKER_PREFLIGHT_SUMMARY_JSON
  export DOCKER_SMOKE_SUMMARY_JSON VALIDATION_SUMMARY_JSON

  VALIDATION_FAILED_COUNT="$failed" \
  RUN_FINISHED_AT="$run_finished_at" \
  RUN_DURATION_SECONDS="$run_duration" \
  DOCKER_AVAILABLE="$docker_available" \
  TOOLFORGE_PYTHON_SUPPORTED="$toolforge_python_supported" \
  python - <<'PY'
import json
import os
from pathlib import Path


def to_int(value: str) -> int:
    return int(value)


def phase_entry(name: str, status: str, duration_key: str, logs: list[str]) -> dict:
    exit_code_text = os.environ.get(f"{name.upper()}_EXIT_CODE", "")
    exit_code = int(exit_code_text) if exit_code_text else None
    return {
        "phase": name,
        "status": status,
        "duration_seconds": to_int(os.environ.get(duration_key, "0")),
        "exit_code": exit_code,
        "logs": logs,
    }


summary = {
    "run_started_at": os.environ["RUN_STARTED_AT"],
    "run_finished_at": os.environ["RUN_FINISHED_AT"],
    "run_duration_seconds": to_int(os.environ["RUN_DURATION_SECONDS"]),
    "python_version": os.environ.get("WORKSPACE_PYTHON_VERSION", "unknown"),
    "python_executable": os.environ.get("WORKSPACE_PYTHON_EXECUTABLE", "unknown"),
    "overall_status": "passed" if to_int(os.environ["VALIDATION_FAILED_COUNT"]) == 0 else "failed",
    "failed_phase_count": to_int(os.environ["VALIDATION_FAILED_COUNT"]),
    "capabilities": {
        "docker_available": os.environ["DOCKER_AVAILABLE"] == "true",
        "toolforge_python_supported": os.environ["TOOLFORGE_PYTHON_SUPPORTED"] == "true",
        "docker_requested": os.environ.get("RUN_DOCKER", "0") == "1",
        "integration_requested": os.environ.get("RUN_INTEGRATION", "0") == "1",
        "toolathlon_profile": os.environ.get("TOOLATHLON_PROFILE", "smoke"),
        "rc_smoke_gate_enforced": os.environ.get("ENFORCE_RC_SMOKE_PROFILE", "0") == "1",
    },
    "phases": [
        phase_entry(
            "toolforge",
            os.environ["TOOLFORGE_STATUS"],
            "TOOLFORGE_DURATION_SECONDS",
            [
                os.environ["TOOLFORGE_PYTHON_LOG"],
                os.environ["TOOLFORGE_INSTALL_LOG"],
                os.environ["TOOLFORGE_DOCTOR_LOG"],
                os.environ["TOOLFORGE_SCHEMA_PATH_SAFETY_LOG"],
                os.environ["TOOLFORGE_VALIDATOR_LOG"],
                os.environ["TOOLFORGE_REGISTRY_LOG"],
                os.environ["TOOLFORGE_CLI_LOG"],
                os.environ["TOOLFORGE_E2E_LOG"],
                os.environ["TOOLFORGE_EVAL_LOG"],
                os.environ["TOOLFORGE_INTEGRATION_LOG"],
            ],
        ),
        phase_entry(
            "agent_skills",
            os.environ["AGENT_SKILLS_STATUS"],
            "AGENT_SKILLS_DURATION_SECONDS",
            [os.environ["AGENT_SKILLS_LIST_LOG"], os.environ["AGENT_SKILLS_EVAL_LOG"]],
        ),
        phase_entry(
            "toolathlon",
            os.environ["TOOLATHLON_STATUS"],
            "TOOLATHLON_DURATION_SECONDS",
            [
                os.environ["TOOLATHLON_BUILD_LOG"],
                os.environ["TOOLATHLON_PREFLIGHT_LOG"],
              os.environ["TOOLATHLON_SMOKE_SUMMARY_JSON"],
                os.environ["TOOLATHLON_PREFLIGHT_SUMMARY_JSON"],
                os.environ["TOOLATHLON_ARTIFACT_BUILD_SUMMARY_JSON"],
            ],
        ),
        phase_entry(
            "docker",
            os.environ["DOCKER_STATUS"],
            "DOCKER_DURATION_SECONDS",
          [
            os.environ["DOCKER_BUILD_LOG"],
            os.environ["DOCKER_PREFLIGHT_LOG"],
            os.environ["DOCKER_SMOKE_SUMMARY_JSON"],
            os.environ["DOCKER_PREFLIGHT_SUMMARY_JSON"],
          ],
        ),
    ],
}

Path(os.environ["VALIDATION_SUMMARY_JSON"]).write_text(
    json.dumps(summary, indent=2, sort_keys=True) + "\n",
    encoding="utf-8",
)
PY

  echo "Validation summary JSON: $VALIDATION_SUMMARY_JSON"
}

if [ "$RUN_INTEGRATION" = "1" ]; then
  marker_args=("-q")
else
  marker_args=("-q" "-m" "not integration and not slow")
fi

# Phase 1: ToolForge validation

toolforge_phase_start="$(date +%s)"

echo -e "${YELLOW}== ToolForge ==${NC}"
if run_python_version_check >"$TOOLFORGE_PYTHON_LOG" 2>&1; then
  cat "$TOOLFORGE_PYTHON_LOG"

  toolforge_failed=0

  if ! run_step "ToolForge install" 300 "$TOOLFORGE_DIR" "$TOOLFORGE_INSTALL_LOG" \
    python -m pip install -e ".[dev]"; then
    toolforge_failed=1
  fi

  if ! run_step "ToolForge doctor" 120 "$TOOLFORGE_DIR" "$TOOLFORGE_DOCTOR_LOG" \
    env PYTHONPATH=. python -m apps.cli.toolforge_cli.main doctor; then
    toolforge_failed=1
  fi

    if ! run_step "ToolForge schema/path/safety tests" 180 "$TOOLFORGE_DIR" "$TOOLFORGE_SCHEMA_PATH_SAFETY_LOG" \
      env PYTHONPATH=. pytest "${marker_args[@]}" \
      tests/test_tool_spec.py \
      tests/test_path_safety.py \
      tests/test_safety_analyzer.py \
      tests/test_package_builder.py; then
    toolforge_failed=1
  fi

    if ! run_step "ToolForge validator tests" 240 "$TOOLFORGE_DIR" "$TOOLFORGE_VALIDATOR_LOG" \
      env PYTHONPATH=. pytest "${marker_args[@]}" \
      tests/test_test_validator.py; then
    toolforge_failed=1
  fi

    if ! run_step "ToolForge registry tests" 240 "$TOOLFORGE_DIR" "$TOOLFORGE_REGISTRY_LOG" \
      env PYTHONPATH=. pytest "${marker_args[@]}" \
      tests/test_registry.py \
      tests/test_registry_cli_exit.py; then
    toolforge_failed=1
  fi

    if ! run_step "ToolForge CLI tests" 300 "$TOOLFORGE_DIR" "$TOOLFORGE_CLI_LOG" \
      env PYTHONPATH=. pytest "${marker_args[@]}" \
      tests/test_cli_command_exit.py \
      tests/test_cli_main_inprocess_coverage.py \
      tests/test_cli_validation_regressions.py; then
    toolforge_failed=1
  fi

    if ! run_step "ToolForge E2E tests" 600 "$TOOLFORGE_DIR" "$TOOLFORGE_E2E_LOG" \
      env PYTHONPATH=. pytest "${marker_args[@]}" \
      tests/test_cli_e2e_csv_cleaner.py \
      tests/test_cli_e2e_json_schema_validator.py \
      tests/test_cli_e2e_local_file_hasher.py; then
    toolforge_failed=1
  fi

    if ! run_step "ToolForge eval tests" 600 "$TOOLFORGE_DIR" "$TOOLFORGE_EVAL_LOG" \
      env PYTHONPATH=. pytest "${marker_args[@]}" \
      tests/test_eval_generator.py \
      tests/test_eval_runner_case_source.py \
      tests/test_eval_runner_expected_failures.py \
      tests/test_ai_spec_generator.py; then
    toolforge_failed=1
  fi

  if [ "$RUN_INTEGRATION" = "1" ]; then
    if ! run_step "ToolForge integration tests" 600 "$TOOLFORGE_DIR" "$TOOLFORGE_INTEGRATION_LOG" \
      env PYTHONPATH=. pytest -q -m integration; then
      toolforge_failed=1
    fi
  else
    echo "ToolForge integration tests skipped (set RUN_INTEGRATION=1 to enable)." > "$TOOLFORGE_INTEGRATION_LOG"
  fi

  if [ "$toolforge_failed" -eq 1 ]; then
    TOOLFORGE_STATUS="failed"
    failed=$((failed + 1))
  else
    TOOLFORGE_STATUS="passed"
  fi
else
  TOOLFORGE_PYTHON_OK=0
  TOOLFORGE_STATUS="unsupported-python"
  failed=$((failed + 1))
  cat "$TOOLFORGE_PYTHON_LOG"
fi
TOOLFORGE_DURATION_SECONDS="$(( $(date +%s) - toolforge_phase_start ))"

echo

# Phase 2: Agent Skills validation

agent_skills_phase_start="$(date +%s)"

echo -e "${YELLOW}== Agent Skills ==${NC}"
if node "$AGENT_SKILLS_DIR/bin/cli.js" list > "$AGENT_SKILLS_LIST_LOG" 2>&1; then
  skill_count=$(find "$AGENT_SKILLS_DIR/skills" -mindepth 2 -maxdepth 2 -type d | wc -l | tr -d ' ')
  echo "✓ Found $skill_count skills"
else
  echo -e "${RED}✗ Agent Skills list failed${NC} (log: $AGENT_SKILLS_LIST_LOG)"
  AGENT_SKILLS_STATUS="failed"
  failed=$((failed + 1))
fi

if node "$AGENT_SKILLS_DIR/bin/cli.js" eval --json > "$AGENT_SKILLS_EVAL_LOG" 2>&1; then
  hard_failures=$(AGENT_SKILLS_EVAL_LOG="$AGENT_SKILLS_EVAL_LOG" python - <<'PY'
import json
import os
from pathlib import Path

arr = json.loads(Path(os.environ['AGENT_SKILLS_EVAL_LOG']).read_text(encoding='utf-8'))
hard = 0
for item in arr:
    for check in item.get('structural', {}).get('checks', []):
        if (not check.get('passed', False)) and check.get('severity') == 'error':
            hard += 1
print(hard)
PY
)
  if [ "$hard_failures" = "0" ]; then
    echo "✓ Agent Skills eval passed (0 hard failures)"
    if [ "$AGENT_SKILLS_STATUS" != "failed" ]; then
      AGENT_SKILLS_STATUS="passed"
    fi
  else
    echo -e "${RED}✗ Agent Skills eval has $hard_failures hard failure(s)${NC}"
    AGENT_SKILLS_STATUS="failed"
    failed=$((failed + 1))
  fi
else
  echo -e "${RED}✗ Agent Skills eval command failed${NC} (log: $AGENT_SKILLS_EVAL_LOG)"
  AGENT_SKILLS_STATUS="failed"
  failed=$((failed + 1))
fi
AGENT_SKILLS_DURATION_SECONDS="$(( $(date +%s) - agent_skills_phase_start ))"

echo

# Phase 3: Toolathlon build + preflight

toolathlon_phase_start="$(date +%s)"

echo -e "${YELLOW}== Toolathlon ==${NC}"
if ! ensure_pyyaml; then
  echo -e "${RED}✗ Failed to install PyYAML dependency required for Toolathlon preflight${NC}"
  TOOLATHLON_STATUS="failed"
  failed=$((failed + 1))
fi

if python "$REPO_ROOT/scripts/run_with_timeout.py" --timeout 1800 -- \
  bash "$TOOLATHLON_DIR/scripts/build_required_mcp_artifacts.sh" 2>&1 | tee "$TOOLATHLON_BUILD_LOG"; then
  echo "✓ Required MCP artifacts built"

  if artifact_summary_gate=$(python - <<PYEOF
import json
from pathlib import Path

summary_path = Path("$TOOLATHLON_ARTIFACT_BUILD_SUMMARY_JSON")

if not summary_path.exists():
    print("missing_summary")
    raise SystemExit(1)

try:
    summary = json.loads(summary_path.read_text(encoding='utf-8'))
except Exception:
    print("invalid_json")
    raise SystemExit(1)

overall_status = summary.get('overall_status')
failed_count = summary.get('failed_count')
package_count = summary.get('package_count')
expected_count = summary.get('expected_package_count')
profile = summary.get('profile')
reason = summary.get('reason')
expected_profile = "$TOOLATHLON_PROFILE"

if profile != expected_profile:
  print(f"profile={profile} expected_profile={expected_profile}")
  raise SystemExit(1)

if overall_status != 'passed':
    if reason:
        print(f"overall_status={overall_status} reason={reason}")
    else:
        print(f"overall_status={overall_status}")
    raise SystemExit(1)

if failed_count != 0:
    print(f"failed_count={failed_count}")
    raise SystemExit(1)

if expected_count is None:
    print("expected_package_count=missing")
    raise SystemExit(1)

if package_count != expected_count:
    print(f"package_count={package_count} expected_package_count={expected_count}")
    raise SystemExit(1)

print(
  f"profile={profile} package_count={package_count} "
  f"expected_package_count={expected_count} failed_count={failed_count} "
  f"overall_status={overall_status}"
)
PYEOF
); then
    if [ -n "$artifact_summary_gate" ]; then
      echo "Artifact summary gate details: $artifact_summary_gate" | tee -a "$TOOLATHLON_BUILD_LOG"
    fi
    echo "✓ MCP artifact summary gate passed"
  else
    echo -e "${RED}✗ MCP artifact summary gate failed${NC} (requirement: overall_status=passed, failed_count=0, package_count=expected_package_count)"
    if [ -n "${artifact_summary_gate:-}" ]; then
      echo "Artifact summary gate details: ${artifact_summary_gate}" | tee -a "$TOOLATHLON_BUILD_LOG"
    fi
    TOOLATHLON_STATUS="failed"
    failed=$((failed + 1))
  fi
else
  echo -e "${RED}✗ MCP artifact build failed or timed out${NC} (log: $TOOLATHLON_BUILD_LOG)"
  TOOLATHLON_STATUS="failed"
  failed=$((failed + 1))
fi

if toolathlon_smoke_gate=$(python - <<PYEOF
import json
from pathlib import Path

summary_path = Path("$TOOLATHLON_SMOKE_SUMMARY_JSON")

if not summary_path.exists():
    print("missing_summary")
    raise SystemExit(1)

summary = json.loads(summary_path.read_text(encoding='utf-8'))
overall_status = summary.get('overall_status')
failed_count = summary.get('failed_count')
target_count = summary.get('target_count')
passed_count = summary.get('passed_count')
profile = summary.get('profile')
expected_profile = "$TOOLATHLON_PROFILE"

if profile != expected_profile:
  print(f"profile={profile} expected_profile={expected_profile}")
  raise SystemExit(1)

if overall_status != 'passed':
    print(f"overall_status={overall_status}")
    raise SystemExit(1)

if failed_count != 0:
    print(f"failed_count={failed_count}")
    raise SystemExit(1)

if passed_count != target_count:
    print(f"passed_count={passed_count} target_count={target_count}")
    raise SystemExit(1)

print(
  f"profile={profile} overall_status={overall_status} "
    f"target_count={target_count} passed_count={passed_count} failed_count={failed_count}"
)
PYEOF
); then
  echo "✓ MCP smoke summary gate passed"
  echo "Smoke summary gate details: $toolathlon_smoke_gate" | tee -a "$TOOLATHLON_BUILD_LOG"
else
  echo -e "${RED}✗ MCP smoke summary gate failed${NC}"
  if [ -n "${toolathlon_smoke_gate:-}" ]; then
    echo "Smoke summary gate details: ${toolathlon_smoke_gate}" | tee -a "$TOOLATHLON_BUILD_LOG"
  fi
  TOOLATHLON_STATUS="failed"
  failed=$((failed + 1))
fi

if python "$TOOLATHLON_DIR/scripts/preflight_mcp_paths.py" \
  --json-output "$TOOLATHLON_PREFLIGHT_SUMMARY_JSON" 2>&1 | tee "$TOOLATHLON_PREFLIGHT_LOG"; then
  if preflight_gate=$(python - <<PYEOF
import json
from pathlib import Path

summary_path = Path("$TOOLATHLON_PREFLIGHT_SUMMARY_JSON")
if not summary_path.exists():
    print("missing_summary")
    raise SystemExit(1)

summary = json.loads(summary_path.read_text(encoding='utf-8'))
profile = summary.get('profile')
expected_profile = "$TOOLATHLON_PROFILE"
missing_count = summary.get('missing_count')

if profile != expected_profile:
    print(f"profile={profile} expected_profile={expected_profile}")
    raise SystemExit(1)

if missing_count != 0:
    print(f"missing_count={missing_count}")
    raise SystemExit(1)

print(f"profile={profile} missing_count={missing_count}")
PYEOF
  ); then
    echo "✓ MCP preflight passed (missing_count = 0)"
    echo "Preflight summary gate details: $preflight_gate" | tee -a "$TOOLATHLON_PREFLIGHT_LOG"
    if [ "$TOOLATHLON_STATUS" != "failed" ]; then
      TOOLATHLON_STATUS="passed"
    fi
  else
    echo -e "${RED}✗ MCP preflight summary gate failed${NC} (requirement: profile matches requested profile and missing_count = 0)"
    if [ -n "${preflight_gate:-}" ]; then
      echo "Preflight summary gate details: ${preflight_gate}" | tee -a "$TOOLATHLON_PREFLIGHT_LOG"
    fi
    TOOLATHLON_STATUS="failed"
    failed=$((failed + 1))
  fi
else
  echo -e "${RED}✗ MCP preflight failed${NC} (log: $TOOLATHLON_PREFLIGHT_LOG)"
  TOOLATHLON_STATUS="failed"
  failed=$((failed + 1))
fi
TOOLATHLON_DURATION_SECONDS="$(( $(date +%s) - toolathlon_phase_start ))"

echo

# Optional phase: Docker validation.
docker_phase_start="$(date +%s)"
if [ "$RUN_DOCKER" = "1" ]; then
  echo -e "${YELLOW}== Docker ==${NC}"

  if run_step "Docker validation" 5400 "$TOOLATHLON_DIR" "$DOCKER_BUILD_LOG" \
    env OUT_DIR="$LOG_DIR" DOCKER_CONTEXT="$DOCKER_CONTEXT" bash scripts/validate_docker.sh; then
    printf '%s\n' "Docker validation completed via $TOOLATHLON_DIR/scripts/validate_docker.sh" > "$DOCKER_PREFLIGHT_LOG"
    DOCKER_STATUS="passed"
  else
    printf '%s\n' "Docker validation failed; inspect $DOCKER_BUILD_LOG for the combined build/smoke/preflight transcript." > "$DOCKER_PREFLIGHT_LOG"
    DOCKER_STATUS="failed"
    failed=$((failed + 1))
  fi

  echo
else
  echo "Docker validation skipped (set RUN_DOCKER=1 to enable)." | tee "$DOCKER_BUILD_LOG" "$DOCKER_PREFLIGHT_LOG" >/dev/null
fi
DOCKER_DURATION_SECONDS="$(( $(date +%s) - docker_phase_start ))"

if [ "$HAVE_GIT" -eq 1 ]; then
  FINAL_GIT_STATUS="$(git -C "$REPO_ROOT" status --porcelain)"
  FINAL_GIT_STATUS_FILTERED="$(printf '%s\n' "$FINAL_GIT_STATUS" | grep -Ev '^[ MARCUD?!]{2} toolathlon-gym-curated/local_servers/.*/(build|dist|\.venv|node_modules)/' || true)"
  if [ "$INITIAL_GIT_STATUS_FILTERED" != "$FINAL_GIT_STATUS_FILTERED" ]; then
    echo -e "${RED}✗ Validation left repository with uncommitted changes${NC}"
    echo "Run: git -C '$REPO_ROOT' status --short"
    failed=$((failed + 1))
  fi
fi

echo "Validation summary:"
if [ "$TOOLFORGE_STATUS" = "unsupported-python" ]; then
  echo "❌ ToolForge - unsupported Python for ToolForge, see $TOOLFORGE_PYTHON_LOG"
elif [ "$TOOLFORGE_STATUS" = "failed" ]; then
  echo "❌ ToolForge - one or more test groups failed (see $TOOLFORGE_INSTALL_LOG, $TOOLFORGE_DOCTOR_LOG, $TOOLFORGE_SCHEMA_PATH_SAFETY_LOG, $TOOLFORGE_VALIDATOR_LOG, $TOOLFORGE_REGISTRY_LOG, $TOOLFORGE_CLI_LOG, $TOOLFORGE_E2E_LOG, $TOOLFORGE_EVAL_LOG, $TOOLFORGE_INTEGRATION_LOG)"
else
  echo "✅ ToolForge - passed"
fi

if [ "$AGENT_SKILLS_STATUS" = "passed" ]; then
  echo "✅ Agent Skills - passed, see $AGENT_SKILLS_EVAL_LOG"
else
  echo "❌ Agent Skills - failed, see $AGENT_SKILLS_EVAL_LOG and $AGENT_SKILLS_LIST_LOG"
fi

if [ "$TOOLATHLON_STATUS" = "passed" ]; then
  echo "✅ Toolathlon - passed, see $TOOLATHLON_PREFLIGHT_LOG"
else
  echo "❌ Toolathlon - failed, see $TOOLATHLON_BUILD_LOG and $TOOLATHLON_PREFLIGHT_LOG"
fi

if [ "$DOCKER_STATUS" = "passed" ]; then
  echo "✅ Docker - passed, see $DOCKER_BUILD_LOG and $DOCKER_PREFLIGHT_LOG"
elif [ "$DOCKER_STATUS" = "failed" ]; then
  echo "❌ Docker - failed, see $DOCKER_BUILD_LOG and $DOCKER_PREFLIGHT_LOG"
else
  echo "⚪ Docker - skipped (set RUN_DOCKER=1), see $DOCKER_BUILD_LOG"
fi

TOOLFORGE_EXIT_CODE="$(status_to_exit_code "$TOOLFORGE_STATUS")"
AGENT_SKILLS_EXIT_CODE="$(status_to_exit_code "$AGENT_SKILLS_STATUS")"
TOOLATHLON_EXIT_CODE="$(status_to_exit_code "$TOOLATHLON_STATUS")"
DOCKER_EXIT_CODE="$(status_to_exit_code "$DOCKER_STATUS")"

write_validation_summary
python "$REPO_ROOT/scripts/sanitize_release_paths.py"

if [ "$failed" -eq 0 ]; then
  echo -e "${GREEN}✓ Workspace validation passed.${NC}"
  exit 0
fi

echo -e "${RED}✗ $failed validation phase(s) failed.${NC}"
exit 1
