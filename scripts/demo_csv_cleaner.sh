#!/usr/bin/env bash
# demo_csv_cleaner.sh — North-star end-to-end demo of the CSV proof path
# Usage: bash scripts/demo_csv_cleaner.sh  (or: make demo)
set -euo pipefail

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
timeout 60 toolforge init . || { echo "Init timed out or failed"; exit 1; }

echo ""
echo "▶ Step 2 — generate csv-cleaner from prompt"
timeout 60 toolforge new tool --from-prompt "Create a tool that cleans CSV files" || { echo "New tool timed out or failed"; exit 1; }

echo ""
echo "▶ Step 3 — generate MCP / Skill / Eval wrappers"
timeout 60 toolforge generate mcp csv-cleaner || { echo "Generate MCP timed out or failed"; exit 1; }
timeout 60 toolforge generate skill csv-cleaner || { echo "Generate skill timed out or failed"; exit 1; }
timeout 60 toolforge generate eval csv-cleaner || { echo "Generate eval timed out or failed"; exit 1; }

echo ""
echo "▶ Step 4 — validate (schema + security + tests + safety)"
toolforge validate csv-cleaner || { echo "Validate failed"; exit 1; }

echo ""
echo "▶ Step 5 — run with a real CSV"
timeout 60 toolforge run csv-cleaner --input input_path=examples/input.csv || { echo "Run timed out or failed"; exit 1; }

echo ""
echo "▶ Step 6 — confirm path-traversal attack is blocked"
# toolforge exits 1 on blocked paths and writes to stderr; capture both streams.
traversal_out=$(timeout 30 toolforge run csv-cleaner --input 'input_path=../../../etc/passwd' 2>&1 || true)
if echo "$traversal_out" | grep -q "Path validation failed"; then
  echo "  ✓ Attack correctly blocked"
else
  echo "  ✗ UNEXPECTED: attack was NOT blocked"
  echo "    Output was: $traversal_out"
  exit 1
fi

echo ""
echo "▶ Step 7 — run eval suite (expects 100% pass rate)"
timeout 60 toolforge eval csv-cleaner || { echo "Eval timed out or failed"; exit 1; }

echo ""
echo "▶ Step 8 — package to .zip"
timeout 60 toolforge package csv-cleaner || { echo "Package timed out or failed"; exit 1; }

echo ""
echo "▶ Step 9 — registry"
timeout 30 toolforge registry list || { echo "Registry list timed out or failed"; exit 1; }
timeout 30 toolforge registry info csv-cleaner || { echo "Registry info timed out or failed"; exit 1; }

echo ""
echo "══════════════════════════════════════════════════════"
echo "  Demo complete — all steps passed ✓"
echo "══════════════════════════════════════════════════════"
echo ""
