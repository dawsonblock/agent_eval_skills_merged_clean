# Release Handoff (2026-05-27)

Repository: agent_eval_skills_merged_clean
Branch: main
Commit: cebce44

## Handoff Type

Repo-local exact-pair attestation refresh.

This handoff records the exact artifact pair currently present in the repository
root and the smoke-profile evidence that verifies against it. It does not change
the workspace classification from `SOURCE_BUNDLE` to a new canonical release
event.

## Artifact Pair

- Release ZIP: `agent_eval_skills_merged_clean-pruned-smoke.zip`
- Release SHA256: `01ffe2f112a76baee38d56863413b4595abd9d0e89b799908442a50382c10f0e`
- Evidence ZIP: `agent_eval_skills_merged_clean-smoke-evidence-2026-05-27.zip`
- Evidence SHA256: `e7ec62bd40c43c49c4e7262fa108888e1e2c4e77ac7a0033fa83e3c6e6a4df73`

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
- Attestation: `RELEASE_ATTESTATION_2026-05-27.md`
