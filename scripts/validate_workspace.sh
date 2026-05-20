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

# Phase 1: ToolForge validation
echo "${YELLOW}== ToolForge ==${NC}"
cd "$REPO_ROOT/ToolForge"
if python -m pip install -e ".[dev]" > /dev/null 2>&1; then
  echo "✓ Dependencies installed"
else
  echo "⚠ Dependency install had warnings (may still work)"
fi

if PYTHONPATH=. python -m apps.cli.toolforge_cli.main doctor > /dev/null 2>&1; then
  echo "✓ Doctor check passed"
else
  echo "${RED}✗ Doctor check failed${NC}"
  failed=$((failed + 1))
fi

if PYTHONPATH=. pytest -q > /dev/null 2>&1; then
  echo "✓ Tests passed"
else
  echo "${RED}✗ Tests failed${NC}"
  failed=$((failed + 1))
fi

cd "$REPO_ROOT"
echo

# Phase 2: Agent Skills validation
echo "${YELLOW}== Agent Skills ==${NC}"
cd "$REPO_ROOT/agent-skills-curated"
if node bin/cli.js list > /tmp/agent_skills_list.txt 2>/dev/null; then
  skill_count=$(find skills -mindepth 2 -maxdepth 2 -type d | wc -l | tr -d ' ')
  echo "✓ Found $skill_count skills"
else
  echo "${RED}✗ Skills list failed${NC}"
  failed=$((failed + 1))
fi

# Enforce structural quality: fail only on hard (error-severity) findings.
if node bin/cli.js eval --json > /tmp/agent_skills_eval.json 2>/dev/null; then
  hard_failures=$(python - <<'PY'
import json
from pathlib import Path
raw = Path('/tmp/agent_skills_eval.json').read_text(encoding='utf-8')
start = raw.find('[')
if start < 0:
    print(1)
    raise SystemExit
arr = json.loads(raw[start:])
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
  echo "${RED}✗ Agent Skills eval command failed${NC}"
  failed=$((failed + 1))
fi

cd "$REPO_ROOT"
echo

# Phase 3: Toolathlon preflight
echo "${YELLOW}== Toolathlon Preflight ==${NC}"
cd "$REPO_ROOT/toolathlon-gym-curated"
if bash scripts/build_required_mcp_artifacts.sh > /tmp/toolathlon_build_artifacts.txt 2>&1; then
  echo "✓ Required MCP artifacts built"
else
  echo "${RED}✗ MCP artifact build failed${NC}"
  tail -n 10 /tmp/toolathlon_build_artifacts.txt || true
  failed=$((failed + 1))
fi

if python scripts/preflight_mcp_paths.py > /tmp/toolathlon_preflight.txt 2>&1; then
  echo "✓ MCP preflight passed"
else
  echo "${RED}✗ MCP preflight failed${NC}"
  tail -n 10 /tmp/toolathlon_preflight.txt || true
  failed=$((failed + 1))
fi

cd "$REPO_ROOT"
echo

# Summary
echo "${YELLOW}== Summary ==${NC}"
if [ $failed -eq 0 ]; then
  echo -e "${GREEN}✓ Workspace validation passed.${NC}"
  exit 0
else
  echo -e "${RED}✗ $failed validation phase(s) failed.${NC}"
  exit 1
fi
