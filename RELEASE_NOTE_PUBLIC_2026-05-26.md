# Release Note: agent_eval_skills_merged_clean (Smoke Candidate Repair)

Historical notice: this note captures the 2026-05-26/2026-05-22 policy reference state and is superseded for current canonical hashes by [RELEASE_ATTESTATION_2026-05-27.md](RELEASE_ATTESTATION_2026-05-27.md) and [release_artifacts/release_lock.json](release_artifacts/release_lock.json).

Date: 2026-05-26
Commit: 03a0c23
Branch: main

## Summary

This update repairs source-bundle smoke-profile evidence and release metadata for `agent_eval_skills_merged_clean`.

The evidence bundle was rebuilt, stale metadata was synchronized across policy and attestation files, and the required smoke/source-bundle gates were re-run successfully.

This note does not constitute a fresh canonical re-attestation of a newly rebuilt release ZIP.

## Historical Canonical Artifact Pair (2026-05-22)

- Release ZIP: `agent_eval_skills_merged_clean-pruned-smoke.zip`
- Evidence ZIP: `agent_eval_skills_merged_clean-smoke-evidence-*.zip`

SHA256 hashes for the current canonical artifact pair are maintained as the single source
of truth in `release_artifacts/release_lock.json` (`release_sha256` / `evidence_sha256`).
Hardcoded hash values in release notes become stale when the release ZIP is rebuilt;
consult `release_lock.json` for authoritative hashes.

## Verification Status

The following checks were executed and passed:

- Source bundle hygiene verification
- Canonical release pair verification
- Release pair verification
- Operator release gate check
- Release classification matrix verification
- Release policy drift validation (`--require-validation-logs`)
- Claims and release identity tests

## Policy Posture

- `release_classification`: `SOURCE_BUNDLE`
- `toolathlon_profile`: `smoke`
- `full_profile_validated`: `false`
- `production_claim_allowed`: `false`

This release may claim smoke-profile validation only.
It must not claim full Toolathlon coverage or production safety certification.
The working tree remains a source bundle, not a newly finalized canonical distribution event.

## Notable Corrections

- Rebuilt missing/required MCP smoke artifacts and verified 3/3 target availability.
- Regenerated fresh validation summaries and evidence contents.
- Regenerated `RELEASE_MANIFEST.json` and reconciled hash references.
- Synchronized root and `dist/release` attestation/hash files.
- Repaired stale evidence-bundle contents without promoting the working tree to a new canonical attestation.

## DeepSeek UI Clarification

DeepSeek local UI assets are present in this branch, including:

- `ToolForge/apps/local_deepseek_demo/`
- `ToolForge/packages/providers/deepseek_client.py`
- `scripts/run_deepseek_tool_ui.sh`

Earlier guidance stating this branch lacked DeepSeek UI is stale for the current repository state.
