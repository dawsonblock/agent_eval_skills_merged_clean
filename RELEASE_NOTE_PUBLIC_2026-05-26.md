# Release Note: agent_eval_skills_merged_clean (Smoke Candidate Repair)

Date: 2026-05-26
Commit: 03a0c23
Branch: main

## Summary

This update repairs source-bundle smoke-profile evidence and release metadata for `agent_eval_skills_merged_clean`.

The evidence bundle was rebuilt, stale metadata was synchronized across policy and attestation files, and the required smoke/source-bundle gates were re-run successfully.

This note does not constitute a fresh canonical re-attestation of a newly rebuilt release ZIP.

## Canonical Artifact Pair

- Release ZIP: `agent_eval_skills_merged_clean-pruned-smoke.zip`
  - SHA256: `88b4514aec9203910b85333a868d64437876b1f7127023bfb37ae2d324b06a43`
- Evidence ZIP: `agent_eval_skills_merged_clean-smoke-evidence-2026-05-22.zip`
  - SHA256: `34c8da07a487aef1fc69fb74d609de427d2e673ed999c5f29fa2de7d5f9bb79a`

These values are maintained as the current source-bundle policy reference in the repository, not as proof that every regenerated ZIP from the working tree has identical bytes.

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
