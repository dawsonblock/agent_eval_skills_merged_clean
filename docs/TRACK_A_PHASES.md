# Track A Phase Guide

This guide defines the release and packaging discipline required before product-layer expansion.

## Phase A1: Canonical Pair Lock

Objective: release identity is hash-bound to one attested pair only.

Required constants source:

- scripts/canonical_release_attestation.env

Canonical pair:

- agent_eval_skills_merged_clean-pruned-smoke.zip
- agent_eval_skills_merged_clean-smoke-evidence-2026-05-22.zip

Rule:

- Only exact filename and SHA256 matches are canonical release.
- Any other archive is triaged as clean new candidate, unbound wrapper/source bundle, dirty archive, or invalid.

## Phase A2: Upload Classification and Pair Verification

Objective: every uploaded archive is deterministically classified.

Scripts:

- scripts/classify_release_upload.sh
- scripts/verify_release_pair.sh

Expected classes:

- canonical_release
- clean_new_candidate
- unbound_wrapper_source_bundle
- dirty_archive
- invalid

## Phase A3: Scope and Claim Discipline

Objective: public claims remain bounded to smoke-profile evidence.

Validated scope:

- ToolForge
- Agent Skills
- Toolathlon smoke profile

Do not claim:

- production-grade
- hostile-code-safe
- full Toolathlon profile validated
- public marketplace ready

## Phase A4: Packaging and Distribution Integrity

Objective: release zip remains metadata-clean and distribution output is reproducible.

Primary scripts:

- scripts/create_release_zip.sh
- scripts/finalize_release_distribution.sh

Forbidden entries include:

- __MACOSX
- ._* files
- .DS_Store
- node_modules
- .validation_logs
- __pycache__
- .pytest_cache
- .mypy_cache
- .ruff_cache
- .venv

Required distribution output:

- dist/release/agent_eval_skills_merged_clean-pruned-smoke.zip
- dist/release/agent_eval_skills_merged_clean-smoke-evidence-2026-05-22.zip
- dist/release/RELEASE_ATTESTATION_2026-05-22.md
- dist/release/SHA256SUMS.txt

## Phase A5: Runtime-Aware Skip Strictness

Objective: SKIP_EXISTING_ARTIFACTS only skips when runtime readiness is fully proven.

Script:

- scripts/verify_skip_existing_artifacts_strict.sh

Required behavior:

- Node skip requires artifact, node_modules, npm tree health, import smoke, runtime smoke.
- Python skip requires artifact, .venv/bin/python3, artifact smoke, runtime smoke.
- If readiness is incomplete, rebuild is mandatory.

## Phase A6: Drift and Policy Guardrails

Objective: fail closed on policy drift before publish gates.

Scripts:

- scripts/verify_release_gate_policy.sh
- scripts/validate_release_policy_drift.sh

Recommended commands:

- make verify-release-gate-policy
- make verify-release-policy-drift
- make verify-release-policy-drift-strict

## Operator Sequence

1. make verify-release-gate-policy
2. make verify-release-policy-drift
3. make verify-skip-strictness
4. make finalize-release-distribution

Use strict drift mode in CI after unified validation has produced current .validation_logs evidence.
