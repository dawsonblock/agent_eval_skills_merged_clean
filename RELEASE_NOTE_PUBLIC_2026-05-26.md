# Release Note: agent_eval_skills_merged_clean (Smoke Candidate Repair)

Date: 2026-05-26
Commit: 03a0c23
Branch: main

## Summary
This update repairs and re-attests the smoke-profile release candidate artifacts for `agent_eval_skills_merged_clean`.

The release package and evidence bundle were rebuilt, hashes were synchronized across policy/attestation files, and all required smoke release gates were re-run successfully.

## Canonical Artifact Pair
- Release ZIP: `agent_eval_skills_merged_clean-pruned-smoke.zip`
  - SHA256: `1cb8032f0dc753747656d588fda09f6dbb6b81d873902f6a01333c27223b7fd5`
- Evidence ZIP: `agent_eval_skills_merged_clean-smoke-evidence-2026-05-22.zip`
  - SHA256: `cce91633dc9b8bf08e0ba0bac9a33f6a09205ce0d05ddd7a2476ba9c4b6bba55`

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

## Notable Corrections
- Rebuilt missing/required MCP smoke artifacts and verified 3/3 target availability.
- Regenerated fresh validation summaries and evidence contents.
- Regenerated `RELEASE_MANIFEST.json` and reconciled hash references.
- Synchronized root and `dist/release` attestation/hash files.

## DeepSeek UI Clarification
DeepSeek local UI assets are present in this branch, including:
- `ToolForge/apps/local_deepseek_demo/`
- `ToolForge/packages/providers/deepseek_client.py`
- `scripts/run_deepseek_tool_ui.sh`

Earlier guidance stating this branch lacked DeepSeek UI is stale for the current repository state.
