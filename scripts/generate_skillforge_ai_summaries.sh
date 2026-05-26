#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
TOOLFORGE_DIR="$REPO_ROOT/ToolForge"
ARTIFACTS_DIR="$REPO_ROOT/release_artifacts"

mkdir -p "$ARTIFACTS_DIR"

RAW_PYTEST_JSON="$(mktemp)"
trap 'rm -f "$RAW_PYTEST_JSON"' EXIT

GEN_TESTS=1
GEN_E2E=1
GEN_VALIDATION=1

usage() {
  cat <<'USAGE'
Usage: bash scripts/generate_skillforge_ai_summaries.sh [--tests-only|--e2e-only|--validation-only]

Options:
  --tests-only       Generate only release_artifacts/skillforge_ai_test_summary.json
  --e2e-only         Generate only release_artifacts/skillforge_ai_csv_cleaner_e2e_summary.json
  --validation-only  Generate only release_artifacts/skillforge_ai_validation_summary.json
  -h, --help         Show this help message
USAGE
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --tests-only)
      GEN_TESTS=1
      GEN_E2E=0
      GEN_VALIDATION=0
      shift
      ;;
    --e2e-only)
      GEN_TESTS=0
      GEN_E2E=1
      GEN_VALIDATION=0
      shift
      ;;
    --validation-only)
      GEN_TESTS=0
      GEN_E2E=0
      GEN_VALIDATION=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage >&2
      exit 1
      ;;
  esac
done

if [ "$GEN_TESTS" -eq 1 ]; then
  echo "Generating SkillForge AI test summary..."
  (
    cd "$TOOLFORGE_DIR"
    PYTHONPATH=. \
    PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 \
    python -m pytest \
      -p pytest_jsonreport.plugin \
      -o addopts= \
      tests/test_skillforge_ai \
      tests/test_test_validator.py \
      tests/integration/test_test_validator_subprocess.py \
      --json-report \
      --json-report-file "$RAW_PYTEST_JSON" \
      -q
  )

  python3 - <<'PY' "$RAW_PYTEST_JSON" "$ARTIFACTS_DIR/skillforge_ai_test_summary.json"
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

raw_path = Path(sys.argv[1])
out_path = Path(sys.argv[2])

raw = json.loads(raw_path.read_text(encoding="utf-8"))
summary = raw.get("summary", {})

payload = {
    "summary_version": "2026-05-25",
    "component": "skillforge_ai",
    "artifact_type": "test_summary",
    "generated_at": datetime.now(timezone.utc).isoformat(),
    "overall_status": "passed" if summary.get("failed", 0) == 0 else "failed",
    "command": (
        "PYTHONPATH=. PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 "
        "python -m pytest -p pytest_jsonreport.plugin -o addopts= "
        "tests/test_skillforge_ai tests/test_test_validator.py "
        "tests/integration/test_test_validator_subprocess.py --json-report -q"
    ),
    "test_counts": {
        "total": summary.get("total", 0),
        "passed": summary.get("passed", 0),
        "failed": summary.get("failed", 0),
        "skipped": summary.get("skipped", 0),
        "xfailed": summary.get("xfailed", 0),
        "xpassed": summary.get("xpassed", 0),
        "errors": summary.get("error", 0),
    },
}

out_path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
print(f"Wrote {out_path}")
PY
fi

if [ "$GEN_E2E" -eq 1 ]; then
  echo "Generating csv-cleaner e2e summary..."
  (
    cd "$TOOLFORGE_DIR"
    PYTHONPATH=. python tests/e2e_scripts/run_csv_cleaner_e2e.py \
      --json-output "$ARTIFACTS_DIR/skillforge_ai_csv_cleaner_e2e_summary.json"
  )
fi

if [ "$GEN_VALIDATION" -eq 1 ]; then
  echo "Generating SkillForge validation summary..."
  (
    cd "$TOOLFORGE_DIR"
    PYTHONPATH=. python -m apps.cli.skillforge_cli.main validate csv-cleaner \
      --summary-json "$ARTIFACTS_DIR/skillforge_ai_validation_summary.json"
  )
fi

echo "SkillForge AI summaries generated:"
if [ "$GEN_TESTS" -eq 1 ]; then
  echo "  - $ARTIFACTS_DIR/skillforge_ai_test_summary.json"
fi
if [ "$GEN_E2E" -eq 1 ]; then
  echo "  - $ARTIFACTS_DIR/skillforge_ai_csv_cleaner_e2e_summary.json"
fi
if [ "$GEN_VALIDATION" -eq 1 ]; then
  echo "  - $ARTIFACTS_DIR/skillforge_ai_validation_summary.json"
fi
