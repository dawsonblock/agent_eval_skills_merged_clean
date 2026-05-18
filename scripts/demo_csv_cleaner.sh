#!/usr/bin/env bash
# demo_csv_cleaner.sh — North-star end-to-end demo of the CSV proof path
# Usage: bash scripts/demo_csv_cleaner.sh  (or: make demo)
set -euo pipefail

# Set module-mode CLI for consistent behavior
export TOOLFORGE_TEST_USE_MODULE_CLI=1

# Cross-platform timeout function
run_with_timeout() {
    local timeout_seconds="$1"
    local kill_after="$2"
    shift 2
    local cmd=("$@")

    # Try GNU timeout first (Linux)
    if command -v timeout &> /dev/null && timeout --version &> /dev/null 2>&1; then
        timeout --kill-after="${kill_after}s" "${timeout_seconds}s" "${cmd[@]}"
    else
        # Fallback to Python for macOS and other systems
        python3 -c "
import subprocess
import sys
import signal
import os

cmd = ${cmd[@]@Q}
timeout = ${timeout_seconds}
kill_after = ${kill_after}

proc = subprocess.Popen(
    cmd,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True,
    start_new_session=True
)

try:
    stdout, stderr = proc.communicate(timeout=timeout)
    sys.stdout.write(stdout)
    sys.stderr.write(stderr)
    sys.exit(proc.returncode)
except subprocess.TimeoutExpired:
    try:
        os.killpg(proc.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    stdout, stderr = proc.communicate()
    sys.stdout.write(stdout)
    sys.stderr.write(stderr)
    sys.exit(124)  # timeout exit code
" "$@"
    fi
}

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
run_with_timeout 60 5 toolforge init . || { echo "Init timed out or failed"; exit 1; }

echo ""
echo "▶ Step 2 — generate csv-cleaner from prompt"
run_with_timeout 120 5 toolforge new tool --from-prompt "Create a tool that cleans CSV files" || { echo "New tool timed out or failed"; exit 1; }

echo ""
echo "▶ Step 3 — generate MCP / Skill / Eval wrappers"
run_with_timeout 60 5 toolforge generate mcp csv-cleaner || { echo "Generate MCP timed out or failed"; exit 1; }
run_with_timeout 60 5 toolforge generate skill csv-cleaner || { echo "Generate skill timed out or failed"; exit 1; }
run_with_timeout 60 5 toolforge generate eval csv-cleaner || { echo "Generate eval timed out or failed"; exit 1; }

echo ""
echo "▶ Step 4 — validate (schema + security + tests + safety)"
run_with_timeout 60 5 toolforge validate csv-cleaner || { echo "Validate failed"; exit 1; }

echo ""
echo "▶ Step 5 — run with a real CSV"
run_with_timeout 60 5 toolforge run csv-cleaner --input input_path=examples/input.csv || { echo "Run timed out or failed"; exit 1; }

echo ""
echo "▶ Step 6 — confirm path-traversal attack is blocked"
# toolforge exits 1 on blocked paths and writes to stderr; capture both streams.
traversal_out=$(run_with_timeout 30 5 toolforge run csv-cleaner --input 'input_path=../../../etc/passwd' 2>&1 || true)
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
run_with_timeout 60 5 toolforge eval csv-cleaner || { echo "Eval timed out or failed"; exit 1; }

echo ""
echo "▶ Step 8 — package to .zip"
run_with_timeout 60 5 toolforge package csv-cleaner || { echo "Package timed out or failed"; exit 1; }

echo ""
echo "▶ Step 9 — registry"
run_with_timeout 30 5 toolforge registry list || { echo "Registry list timed out or failed"; exit 1; }
run_with_timeout 30 5 toolforge registry info csv-cleaner || { echo "Registry info timed out or failed"; exit 1; }

echo ""
echo "══════════════════════════════════════════════════════"
echo "  Demo complete — all steps passed ✓"
echo "══════════════════════════════════════════════════════"
echo ""
