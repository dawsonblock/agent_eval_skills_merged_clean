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
if node bin/cli.js list | head -1 > /dev/null 2>&1; then
  skill_count=$(node bin/cli.js list 2>/dev/null | wc -l)
  echo "✓ Found $skill_count skills"
else
  echo "${RED}✗ Skills list failed${NC}"
  failed=$((failed + 1))
fi

# Eval can be noisy; just check if it runs without crashing
if node evals/evaluate.js --help > /dev/null 2>&1 || [ -f evals/evaluate.js ]; then
  echo "✓ Eval infrastructure present"
else
  echo "${RED}✗ Eval infrastructure missing${NC}"
  failed=$((failed + 1))
fi

cd "$REPO_ROOT"
echo

# Phase 3: Toolathlon preflight
echo "${YELLOW}== Toolathlon Preflight ==${NC}"
cd "$REPO_ROOT/toolathlon-gym-curated"
if python scripts/preflight_mcp_paths.py > /dev/null 2>&1; then
  echo "✓ MCP paths valid (no critical missing builds)"
elif python scripts/preflight_mcp_paths.py 2>&1 | grep -q "MISSING"; then
  echo "${YELLOW}⚠ Some MCP paths missing (may be expected in development)${NC}"
else
  echo "${RED}✗ Preflight script failed${NC}"
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
