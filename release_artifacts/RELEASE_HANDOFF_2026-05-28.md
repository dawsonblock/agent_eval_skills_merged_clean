# Release Handoff (2026-05-28)

Repository: agent_eval_skills_merged_clean
Branch: main
Base commit before this patch set: fa75fa1

## Handoff Type

Canonical-pair pipeline hardening and active-doc hash alignment.

This handoff captures script contract repairs, ordering fixes, smoke-hygiene hardening,
and current-state documentation updates that keep release claims aligned with lock-bound artifacts.

## Canonical Artifact Pair (lock-bound)

- Release ZIP: `agent_eval_skills_merged_clean-pruned-smoke.zip`
- Release SHA256: `01ffe2f112a76baee38d56863413b4595abd9d0e89b799908442a50382c10f0e`
- Evidence ZIP: `agent_eval_skills_merged_clean-smoke-evidence-2026-05-27.zip`
- Evidence SHA256: `e7ec62bd40c43c49c4e7262fa108888e1e2c4e77ac7a0033fa83e3c6e6a4df73`

## Changes Included

### Pipeline Contract Fixes

- Added argparse support to:
  - `scripts/write_validation_summary.py`
  - `scripts/build_evidence_zip.py`
  - `scripts/verify_release_pair.py`
- Added `--pre-evidence` mode to `scripts/verify_release_pair.py`.
- Reordered smoke evidence flow in `scripts/collect_smoke_evidence.sh` to:
  1. Ensure/build canonical release ZIP
  2. Run smoke checks
  3. Run pre-evidence pair verification
  4. Sanitize logs
  5. Write validation summary
  6. Build evidence ZIP
  7. Run final pair verification
- Updated `scripts/validate_release_smoke.sh` to rely on ordered smoke evidence collection,
  then run final pair verification and root tests.

### Hygiene/Policy Hardening

- Added explicit `ToolForge/.skillforge` exclusion in `.release-config/forbidden_entries.txt`.
- Converted `scripts/install_toolathlon_smoke_deps.sh` into a smoke-safe no-op with guidance.

### Active Documentation Alignment

- Updated `DEPLOYMENT.md` canonical pair hashes to lock-aligned current values.
- Updated `WORKSPACE_HEALTH_DASHBOARD.md` canonical pair hashes to lock-aligned current values.
- Marked `RELEASE_NOTE_PUBLIC_2026-05-26.md` as historical/superseded for current canonical references.

## Validation Snapshot (this run)

- `pytest -q tests/test_release_identity.py` -> 9 passed
- `pytest -q tests` -> 11 passed
- `python3 scripts/verify_release_pair.py` -> PASS
- `python3 scripts/check_release_hash_consistency.py` -> PASS
- Fresh-extraction simulation from canonical release ZIP:
  - Extracted archive and executed scoped tests in extracted tree
  - Result: 367 passed, 3 warnings (expected OPENAI_API_KEY fallback warnings)

## Scope Statement

Validated scope:

- ToolForge
- Agent Skills structural checks in release gate context
- Toolathlon smoke profile release flow
- Canonical release/evidence pair verification logic

Out of scope:

- Full Toolathlon profile readiness
- Production/hard-hostile-code security posture

## Source Of Truth

- `release_artifacts/release_lock.json`
- `RELEASE_ATTESTATION_2026-05-27.md`
- `RELEASE_EVIDENCE_MANIFEST_2026-05-27.json`
