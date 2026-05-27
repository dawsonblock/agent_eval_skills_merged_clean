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
- Release SHA256: `88b4514aec9203910b85333a868d64437876b1f7127023bfb37ae2d324b06a43`
- Evidence ZIP: `agent_eval_skills_merged_clean-smoke-evidence-2026-05-22.zip`
- Evidence SHA256: `34c8da07a487aef1fc69fb74d609de427d2e673ed999c5f29fa2de7d5f9bb79a`

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
