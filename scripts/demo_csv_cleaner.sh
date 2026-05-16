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
toolforge init .

echo ""
echo "▶ Step 2 — generate csv-cleaner from prompt"
toolforge new tool --from-prompt "Create a tool that cleans CSV files"

echo ""
echo "▶ Step 3 — generate MCP / Skill / Eval wrappers"
toolforge generate mcp   csv-cleaner
toolforge generate skill csv-cleaner
toolforge generate eval  csv-cleaner

echo ""
echo "▶ Step 4 — validate (schema + security + tests + safety)"
toolforge validate csv-cleaner

echo ""
echo "▶ Step 5 — run with a real CSV"
toolforge run csv-cleaner --input input_path=examples/input.csv

echo ""
echo "▶ Step 6 — confirm path-traversal attack is blocked"
# toolforge exits 1 on blocked paths and writes to stderr; capture both streams.
traversal_out=$(toolforge run csv-cleaner --input 'input_path=../../../etc/passwd' 2>&1 || true)
if echo "$traversal_out" | grep -q "Path validation failed"; then
  echo "  ✓ Attack correctly blocked"
else
  echo "  ✗ UNEXPECTED: attack was NOT blocked"
  echo "    Output was: $traversal_out"
  exit 1
fi

echo ""
echo "▶ Step 7 — run eval suite (expects 100% pass rate)"
toolforge eval csv-cleaner

echo ""
echo "▶ Step 8 — package to .zip"
toolforge package csv-cleaner

echo ""
echo "▶ Step 9 — registry"
toolforge registry list
toolforge registry info csv-cleaner

echo ""
echo "══════════════════════════════════════════════════════"
echo "  Demo complete — all steps passed ✓"
echo "══════════════════════════════════════════════════════"
echo ""
