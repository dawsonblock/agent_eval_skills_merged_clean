#!/usr/bin/env bash
# Unified workspace validation script
# Validates ToolForge, Agent Skills, and Toolathlon components

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && cd .. && pwd)"
echo "Workspace root: $REPO_ROOT"
echo

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

failed=0
HAVE_GIT=0
INITIAL_GIT_STATUS=""
LOG_ROOT="$REPO_ROOT/.validation_logs"
mkdir -p "$LOG_ROOT"
if git -C "$REPO_ROOT" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  HAVE_GIT=1
  INITIAL_GIT_STATUS="$(git -C "$REPO_ROOT" status --porcelain)"
else
  echo "⚠ Not a Git checkout; skipping dirty-tree check"
fi
LOG_DIR="$(mktemp -d "$LOG_ROOT/run.XXXXXX")"
TOOLFORGE_INSTALL_LOG="$LOG_DIR/toolforge_install.log"
TOOLFORGE_DOCTOR_LOG="$LOG_DIR/toolforge_doctor.log"
TOOLFORGE_CORE_TESTS_LOG="$LOG_DIR/toolforge_core_tests.log"
TOOLFORGE_CLI_TESTS_LOG="$LOG_DIR/toolforge_cli_tests.log"
TOOLFORGE_E2E_TESTS_LOG="$LOG_DIR/toolforge_e2e_tests.log"
TOOLFORGE_EVAL_TESTS_LOG="$LOG_DIR/toolforge_eval_tests.log"
AGENT_SKILLS_LIST_LOG="$LOG_DIR/agent_skills_list.txt"
AGENT_SKILLS_EVAL_LOG="$LOG_DIR/agent_skills_eval.json"
AGENT_SKILLS_EVAL_ERR_LOG="$LOG_DIR/agent_skills_eval.err"
TOOLATHLON_BUILD_LOG="$LOG_DIR/toolathlon_build_artifacts.log"
TOOLATHLON_PREFLIGHT_LOG="$LOG_DIR/toolathlon_preflight.log"

echo "Log directory: $LOG_DIR"

run_step() {
  local label="$1"
  local timeout="$2"
  local cwd="$3"
  local log_file="$4"
  shift 4
  local command="$*"

  echo "${YELLOW}→ $label${NC}"
  if (cd "$cwd" && python "$REPO_ROOT/scripts/run_with_timeout.py" --timeout "$timeout" -- bash -c "$command") 2>&1 | tee "$log_file"; then
    echo "✓ $label"
    return 0
  fi

  echo "${RED}✗ $label failed${NC} (log: $log_file)"
  return 1
}

# Phase 1: ToolForge validation
echo "${YELLOW}== ToolForge ==${NC}"
TOOLFORGE_DIR="$REPO_ROOT/ToolForge"
if ! run_step "ToolForge install" 300 "$TOOLFORGE_DIR" "$TOOLFORGE_INSTALL_LOG" "python -m pip install -e '.[dev]'"; then
  failed=$((failed + 1))
fi

if ! run_step "ToolForge doctor" 120 "$TOOLFORGE_DIR" "$TOOLFORGE_DOCTOR_LOG" "PYTHONPATH=. python -m apps.cli.toolforge_cli.main doctor"; then
  failed=$((failed + 1))
fi

if ! run_step "ToolForge core tests" 180 "$TOOLFORGE_DIR" "$TOOLFORGE_CORE_TESTS_LOG" "env PYTHONPATH=. pytest -q tests/test_tool_spec.py tests/test_path_safety.py tests/test_safety_analyzer.py tests/test_package_builder.py tests/test_tool_schema.py tests/test_validators.py tests/test_repo_hygiene.py tests/test_errors.py tests/test_registry.py tests/test_registry_cli_exit.py tests/test_test_validator.py tests/test_skill_generator.py tests/test_tool_generator.py tests/test_mcp_generator.py tests/test_spec_from_prompt.py tests/test_doc_generator.py tests/test_example_specs.py tests/test_logger.py"; then
  failed=$((failed + 1))
fi

if ! run_step "ToolForge CLI tests" 240 "$TOOLFORGE_DIR" "$TOOLFORGE_CLI_TESTS_LOG" "env PYTHONPATH=. pytest -q tests/test_cli_command_exit.py tests/test_cli_main_inprocess_coverage.py tests/test_cli_validation_regressions.py"; then
  failed=$((failed + 1))
fi

if ! run_step "ToolForge E2E tests" 600 "$TOOLFORGE_DIR" "$TOOLFORGE_E2E_TESTS_LOG" "env PYTHONPATH=. pytest -q tests/test_cli_e2e_*.py"; then
  failed=$((failed + 1))
fi

if ! run_step "ToolForge eval tests" 600 "$TOOLFORGE_DIR" "$TOOLFORGE_EVAL_TESTS_LOG" "env PYTHONPATH=. pytest -q tests/test_eval_*.py tests/test_ai_spec_generator.py tests/test_eval_runner_case_source.py tests/test_eval_runner_expected_failures.py"; then
  failed=$((failed + 1))
fi

cd "$REPO_ROOT"
echo

# Phase 2: Agent Skills validation
echo "${YELLOW}== Agent Skills ==${NC}"
cd "$REPO_ROOT/agent-skills-curated"
if node bin/cli.js list > "$AGENT_SKILLS_LIST_LOG" 2>&1; then
  skill_count=$(find skills -mindepth 2 -maxdepth 2 -type d | wc -l | tr -d ' ')
  echo "✓ Found $skill_count skills"
else
  echo "${RED}✗ Skills list failed${NC} (log: $AGENT_SKILLS_LIST_LOG)"
  failed=$((failed + 1))
fi

# Enforce structural quality: fail only on hard (error-severity) findings.
if node bin/cli.js eval --json > "$AGENT_SKILLS_EVAL_LOG" 2>"$AGENT_SKILLS_EVAL_ERR_LOG"; then
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
  else
    echo "${RED}✗ Agent Skills eval has $hard_failures hard failure(s)${NC}"
    failed=$((failed + 1))
  fi
else
  echo "${RED}✗ Agent Skills eval command failed${NC} (json: $AGENT_SKILLS_EVAL_LOG, stderr: $AGENT_SKILLS_EVAL_ERR_LOG)"
  failed=$((failed + 1))
fi

cd "$REPO_ROOT"
echo

# Phase 3: Toolathlon preflight
echo "${YELLOW}== Toolathlon Preflight ==${NC}"
cd "$REPO_ROOT/toolathlon-gym-curated"
if python "$REPO_ROOT/scripts/run_with_timeout.py" --timeout 300 -- bash scripts/build_required_mcp_artifacts.sh 2>&1 | tee "$TOOLATHLON_BUILD_LOG"; then
  echo "✓ Required MCP artifacts built"
else
  echo "${RED}✗ MCP artifact build failed or timed out${NC} (log: $TOOLATHLON_BUILD_LOG)"
  tail -n 20 "$TOOLATHLON_BUILD_LOG" || true
  failed=$((failed + 1))
fi

if python scripts/preflight_mcp_paths.py 2>&1 | tee "$TOOLATHLON_PREFLIGHT_LOG"; then
  echo "✓ MCP preflight passed"
else
  echo "${RED}✗ MCP preflight failed${NC} (log: $TOOLATHLON_PREFLIGHT_LOG)"
  tail -n 20 "$TOOLATHLON_PREFLIGHT_LOG" || true
  failed=$((failed + 1))
fi

cd "$REPO_ROOT"
echo

if [ "$HAVE_GIT" -eq 1 ]; then
  FINAL_GIT_STATUS="$(git -C "$REPO_ROOT" status --porcelain)"
  if [ "$INITIAL_GIT_STATUS" != "$FINAL_GIT_STATUS" ]; then
    echo "${RED}✗ Validation left repository with uncommitted changes${NC}"
    echo "Run: git -C '$REPO_ROOT' status --short"
    failed=$((failed + 1))
  fi
fi

# Summary
echo "${YELLOW}== Summary ==${NC}"
if [ $failed -eq 0 ]; then
  echo -e "${GREEN}✓ Workspace validation passed.${NC}"
  exit 0
else
  echo -e "${RED}✗ $failed validation phase(s) failed.${NC}"
  echo "Validation failed. See $LOG_DIR"
  exit 1
fi
