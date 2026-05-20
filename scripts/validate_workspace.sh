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
INITIAL_GIT_STATUS="$(git -C "$REPO_ROOT" status --porcelain)"
LOG_DIR="$(mktemp -d /tmp/validate_workspace.XXXXXX)"
TOOLFORGE_INSTALL_LOG="$LOG_DIR/toolforge_install.log"
TOOLFORGE_DOCTOR_LOG="$LOG_DIR/toolforge_doctor.log"
TOOLFORGE_PYTEST_LOG="$LOG_DIR/toolforge_pytest.log"
AGENT_SKILLS_LIST_LOG="$LOG_DIR/agent_skills_list.txt"
AGENT_SKILLS_EVAL_LOG="$LOG_DIR/agent_skills_eval.json"
AGENT_SKILLS_EVAL_ERR_LOG="$LOG_DIR/agent_skills_eval.err"
TOOLATHLON_BUILD_LOG="$LOG_DIR/toolathlon_build_artifacts.log"
TOOLATHLON_PREFLIGHT_LOG="$LOG_DIR/toolathlon_preflight.log"

echo "Log directory: $LOG_DIR"

# Phase 1: ToolForge validation
echo "${YELLOW}== ToolForge ==${NC}"
cd "$REPO_ROOT/ToolForge"
if python -m pip install -e ".[dev]" 2>&1 | tee "$TOOLFORGE_INSTALL_LOG"; then
  echo "✓ Dependencies installed"
else
  echo "${RED}✗ Dependency install failed${NC} (log: $TOOLFORGE_INSTALL_LOG)"
  failed=$((failed + 1))
fi

if PYTHONPATH=. python -m apps.cli.toolforge_cli.main doctor 2>&1 | tee "$TOOLFORGE_DOCTOR_LOG"; then
  echo "✓ Doctor check passed"
else
  echo "${RED}✗ Doctor check failed${NC} (log: $TOOLFORGE_DOCTOR_LOG)"
  failed=$((failed + 1))
fi

if python "$REPO_ROOT/scripts/run_with_timeout.py" --timeout 240 -- env PYTHONPATH=. pytest -q 2>&1 | tee "$TOOLFORGE_PYTEST_LOG"; then
  echo "✓ Tests passed"
else
  echo "${RED}✗ Tests failed or timed out${NC} (log: $TOOLFORGE_PYTEST_LOG)"
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

FINAL_GIT_STATUS="$(git -C "$REPO_ROOT" status --porcelain)"
if [ "$INITIAL_GIT_STATUS" != "$FINAL_GIT_STATUS" ]; then
  echo "${RED}✗ Validation left repository with uncommitted changes${NC}"
  echo "Run: git -C '$REPO_ROOT' status --short"
  failed=$((failed + 1))
fi

# Summary
echo "${YELLOW}== Summary ==${NC}"
if [ $failed -eq 0 ]; then
  echo -e "${GREEN}✓ Workspace validation passed.${NC}"
  exit 0
else
  echo -e "${RED}✗ $failed validation phase(s) failed.${NC}"
  exit 1
fi
