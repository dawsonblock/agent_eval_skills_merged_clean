# Public Release Note

Date: 2026-05-28
Repository: agent_eval_skills_merged_clean
Release classification: Verifiable smoke-release wrapper for controlled local evaluation

## Canonical Release Artifacts

This release is bound to the canonical artifact pair declared in `release_artifacts/release_lock.json`.

1. Release archive
   - Filename: `agent_eval_skills_merged_clean-pruned-smoke.zip`
    - SHA256: `e313cb5de93105e653dfd845763a870b45a0504dfb7515a380b9cee83108f22d`

2. Evidence bundle
   - Filename: `agent_eval_skills_merged_clean-smoke-evidence-2026-05-31.zip`
   - SHA256: `2b1774a0e68606b633351d4f25e6ac7ef1aba0c2401927766da0fb01e6fb48a8`

## Verification Status

The required checks pass for the canonical pair:

1. `python3 scripts/verify_release_pair.py` -> PASS
2. `pytest -q tests` -> 11 passed
3. `python3 scripts/check_release_hash_consistency.py` -> PASS
4. `python3 scripts/check_source_bundle_hygiene.py <final-wrapper.zip>` -> PASS
5. `bash scripts/verify_source_bundle_hygiene.sh --zip <final-wrapper.zip>` -> PASS

## Scope Covered By Evidence

- ToolForge validation under Python 3.12
- Agent Skills package validation with quality warnings tracked
- Toolathlon smoke validation for `rail_12306` and `filesystem` after smoke build step
- Canonical release/evidence pair verification and source-bundle hygiene checks

## Artifact Identity Policy

- The final evidence SHA256 is authoritative in `release_artifacts/release_lock.json`.
- Evidence-internal `release_hashes.json` uses lock-governed semantics for evidence hash reporting (`external-lock-governed`) to avoid ZIP self-hash circularity.
- Any wrapper/source upload or regenerated ZIP with different bytes is out of scope until a new manifest plus attestation rebinding is produced.

## Non-Claims

This release does **not** claim:

- production deployment readiness
- security audit certification
- full Toolathlon profile completion
- uniformly high quality across all skills
- raw-extraction smoke runtime without dependency build steps

## Final Statement

This is a verifiable smoke-release wrapper for local agent-tool evaluation and curated skill packaging. The wrapper includes the canonical smoke release ZIP, evidence ZIP, and release lock. The release pair verifies successfully, root release tests pass, ToolForge validates under Python 3.12, Agent Skills package validation passes with quality warnings tracked, and Toolathlon smoke passes for `rail_12306` and `filesystem` after the smoke build step. The full Toolathlon profile remains experimental. This is not a production deployment package or security-audited sandbox.
