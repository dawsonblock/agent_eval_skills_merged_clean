# Release Handoff (2026-05-27)

Repository: agent_eval_skills_merged_clean
Branch: main
Commit: 3b6a771

## Handoff Type

Repo-local exact-pair attestation refresh.

This handoff records the exact artifact pair currently present in the repository
root and the smoke-profile evidence that verifies against it. It does not change
the workspace classification from `SOURCE_BUNDLE` to a new canonical release
event.

## Artifact Pair

- Release ZIP: `agent_eval_skills_merged_clean-pruned-smoke.zip`
- Release SHA256: `1cb8032f0dc753747656d588fda09f6dbb6b81d873902f6a01333c27223b7fd5`
- Evidence ZIP: `agent_eval_skills_merged_clean-smoke-evidence-2026-05-22.zip`
- Evidence SHA256: `96e7f2633f91e90302a6150a3136130a6ae4014287d8ab1cf48d90ae97cbc2e0`

## Gate Snapshot

- Evidence bundle policy check: passed
- Release pair check: passed in `SOURCE_BUNDLE` mode
- Operator release gate check: passed
- Release policy drift check: passed

## Scope Statement

Validated scope:

- ToolForge
- Agent Skills
- Toolathlon smoke profile

Retained but not release-validated:

- Full Toolathlon profile
- all task material
- full MCP server set
- production deployment
- hostile-code safety

## Source Of Truth

- Root manifest: `RELEASE_EVIDENCE_MANIFEST_2026-05-27.json`
- Release-artifacts manifest: `release_artifacts/RELEASE_EVIDENCE_MANIFEST_2026-05-27.json`
- Attestation: `RELEASE_ATTESTATION_2026-05-27.md`
