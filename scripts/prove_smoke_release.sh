#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$ROOT"

export TOOLATHLON_PROFILE=smoke
export ENFORCE_RC_SMOKE_PROFILE=1

python - <<'PY'
import sys
if not ((3, 9) <= sys.version_info[:2] < (3, 13)):
    raise SystemExit(
        f"Unsupported Python {sys.version.split()[0]}; expected >=3.9,<3.13"
    )
PY

echo "[1/11] ToolForge compile check"
python -m compileall -q ToolForge/packages ToolForge/apps ToolForge/skillforge_ai ToolForge/tests

echo "[2/11] ToolForge core tests"
(
  cd ToolForge
  python -m pytest \
    tests/test_tool_spec.py \
    tests/test_path_safety.py \
    tests/test_safety_analyzer.py \
    tests/test_validators.py \
    tests/test_registry.py \
    -q
)

echo "[3/11] SkillForge AI tests"
(
  cd ToolForge
  python -m pytest tests/test_skillforge_ai tests/test_tool_spec.py -q
)

echo "[4/11] ToolForge security and lifecycle policy tests"
(
  cd ToolForge
  python -m pytest \
    tests/test_dangerous_tool_specs.py \
    tests/test_security_policy_expanded.py \
    tests/test_skillforge_lifecycle.py \
    -q
)

echo "[5/11] Root release identity and claims policy tests"
PYTHONPATH=ToolForge python -m pytest tests/test_release_identity.py tests/test_claims_policy.py -q

echo "[6/11] Agent skills structural eval"
(
  cd agent-skills-curated
  node bin/cli.js eval --json
)

echo "[7/11] Toolathlon smoke preflight and smoke checks"
bash scripts/check_toolathlon_smoke_profile.sh

echo "[8/11] Workspace validation"
bash scripts/validate_workspace.sh

echo "[9/11] Release classification matrix"
bash scripts/verify_release_classification_matrix.sh

echo "[10/11] Policy drift check"
bash scripts/validate_release_policy_drift.sh --require-validation-logs

echo "[11/12] Sanitize release-facing JSON paths"
python scripts/sanitize_release_paths.py

echo "[12/12] Absolute-path leak check"
python scripts/check_no_absolute_local_paths.py --strict

echo "Smoke release proof completed."
