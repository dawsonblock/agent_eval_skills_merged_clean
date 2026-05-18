#!/usr/bin/env bash
# demo_csv_cleaner.sh — North-star end-to-end demo of the CSV proof path
# Usage: bash scripts/demo_csv_cleaner.sh  (or: make demo)
set -euo pipefail

# Set module-mode CLI for consistent behavior
export TOOLFORGE_TEST_USE_MODULE_CLI=1

DEMO_DIR="$(mktemp -d /tmp/toolforge_demo_XXXX)"
trap 'rm -rf "$DEMO_DIR"' EXIT

echo ""
echo "══════════════════════════════════════════════════════"
echo "  ToolForge  ·  CSV Cleaner Proof Path Demo"
echo "══════════════════════════════════════════════════════"
echo "  Workspace: $DEMO_DIR"
echo ""

cd "$DEMO_DIR"

echo "▶ Step 1 — init workspace"
timeout --kill-after=5s 60s toolforge init . || { echo "Init timed out or failed"; exit 1; }

echo ""
echo "▶ Step 2 — generate csv-cleaner from prompt"
timeout --kill-after=5s 120s toolforge new tool --from-prompt "Create a tool that cleans CSV files" || { echo "New tool timed out or failed"; exit 1; }

echo ""
echo "▶ Step 3 — generate MCP / Skill / Eval wrappers"
timeout --kill-after=5s 60s toolforge generate mcp csv-cleaner || { echo "Generate MCP timed out or failed"; exit 1; }
timeout --kill-after=5s 60s toolforge generate skill csv-cleaner || { echo "Generate skill timed out or failed"; exit 1; }
timeout --kill-after=5s 60s toolforge generate eval csv-cleaner || { echo "Generate eval timed out or failed"; exit 1; }

echo ""
echo "▶ Step 4 — validate (schema + security + tests + safety)"
timeout --kill-after=5s 60s toolforge validate csv-cleaner || { echo "Validate failed"; exit 1; }

echo ""
echo "▶ Step 5 — run with a real CSV"
timeout --kill-after=5s 60s toolforge run csv-cleaner --input input_path=examples/input.csv || { echo "Run timed out or failed"; exit 1; }

echo ""
echo "▶ Step 6 — confirm path-traversal attack is blocked"
# toolforge exits 1 on blocked paths and writes to stderr; capture both streams.
traversal_out=$(timeout --kill-after=5s 30s toolforge run csv-cleaner --input 'input_path=../../../etc/passwd' 2>&1 || true)
# Remove newlines for grep matching
traversal_out_clean=$(echo "$traversal_out" | tr '\n' ' ')
if echo "$traversal_out_clean" | grep -qi "path validation failed\|resolved outside allowed\|error.*exit 1"; then
  echo "  ✓ Attack correctly blocked"
else
  echo "  ✗ UNEXPECTED: attack was NOT blocked"
  echo "    Output was: $traversal_out"
  exit 1
fi

echo ""
echo "▶ Step 7 — run eval suite (expects 100% pass rate)"
timeout --kill-after=5s 60s toolforge eval csv-cleaner || { echo "Eval timed out or failed"; exit 1; }

echo ""
echo "▶ Step 8 — package to .zip"
timeout --kill-after=5s 60s toolforge package csv-cleaner || { echo "Package timed out or failed"; exit 1; }

echo ""
echo "▶ Step 9 — registry"
timeout --kill-after=5s 30s toolforge registry list || { echo "Registry list timed out or failed"; exit 1; }
timeout --kill-after=5s 30s toolforge registry info csv-cleaner || { echo "Registry info timed out or failed"; exit 1; }

echo ""
echo "══════════════════════════════════════════════════════"
echo "  Demo complete — all steps passed ✓"
echo "══════════════════════════════════════════════════════"
echo ""
