# Release Attestation — 2026-05-27

This document records a repo-local attestation event for the exact artifact pair
currently present in the repository root. It does not, by itself, promote the
mutable working tree to a new canonical distribution event. The workspace
classification in [RELEASE_STATUS.json](RELEASE_STATUS.json) remains
`SOURCE_BUNDLE`.

**Release Label:** agent_eval_skills_merged_clean exact-pair repo-local attestation
**Release Date:** 2026-05-27
**Git Commit:** 3b6a7718165b73264d31cff92969ffb4073a5d43
**Git Branch:** main

## Artifact Pair

| Artifact | SHA256 |
| --- | --- |
| `agent_eval_skills_merged_clean-pruned-smoke.zip` | `1cb8032f0dc753747656d588fda09f6dbb6b81d873902f6a01333c27223b7fd5` |
| `agent_eval_skills_merged_clean-smoke-evidence-2026-05-22.zip` | `96e7f2633f91e90302a6150a3136130a6ae4014287d8ab1cf48d90ae97cbc2e0` |

## Scope

This attestation binds only the exact files above.

- It confirms the evidence bundle verifies against the paired release ZIP.
- It confirms the current source-bundle policy gates pass for this pair.
- It does not declare that a newly rebuilt ZIP from the current working tree has identical bytes.
- It does not replace the workflow-level `SOURCE_BUNDLE` posture with a new canonical release event.

## Verification Snapshot

- `bash scripts/verify_evidence_bundle.sh --evidence agent_eval_skills_merged_clean-smoke-evidence-2026-05-22.zip` — passed
- `bash scripts/verify_release_pair.sh` — passed in `SOURCE_BUNDLE` mode
- `bash scripts/operator_release_gate_check.sh` — passed
- `bash scripts/validate_release_policy_drift.sh --require-validation-logs` — passed

## Source Of Truth

- Manifest: `RELEASE_EVIDENCE_MANIFEST_2026-05-27.json`
- Handoff: `release_artifacts/RELEASE_HANDOFF_2026-05-27.md`
- Validation profile: `smoke`
- Workspace classification at attestation time: `SOURCE_BUNDLE`

## Sign-off

This repo-local attestation supersedes ad hoc repair notes for the exact pair
listed above, while preserving the distinction between historical canonical
release metadata and the current mutable workspace.
