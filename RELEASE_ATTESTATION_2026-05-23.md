# Release Attestation — 2026-05-23

**Release Label:** agent_eval_skills_merged_clean pruned-smoke RC
**Release Date:** 2026-05-23
**Git Commit:** a0b34ab7f88906ef4699a5edb43b4d8d5c1ff153
**Git Branch:** main

---

## Archive Artifacts

| Artifact | SHA256 |
|---|---|
| `agent_eval_skills_merged_clean-pruned-smoke.zip` | `8a94525e47c3c0bef54234435512ae4f8b8b53aa3eef3776115b2f4205d6d46e` |
| `agent_eval_skills_merged_clean-smoke-evidence-2026-05-23.zip` | `437c6048a12c69428b4c900b8dc5a2ce848422e30cb000180bdd6036f1e40830` |

---

## Validation Summary

| Phase | Status |
|---|---|
| ToolForge (98 tests) | ✅ passed |
| Agent Skills (23 skills) | ✅ passed |
| Toolathlon smoke (3/3 targets) | ✅ passed |
| Docker smoke (3/3 targets, separate run) | ✅ passed |
| SKIP_EXISTING_ARTIFACTS gate | ✅ verified |

- **Validation run:** 2026-05-23T20:47:11Z → 2026-05-23T20:47:54Z (43 s)
- **Docker separate run checked_at:** 2026-05-23T20:49:14Z
- **Toolathlon profile:** smoke
- **RC smoke gate enforced:** yes
- **Python version:** 3.12.9

---

## Evidence Bundle Contents

The evidence bundle `agent_eval_skills_merged_clean-smoke-evidence-2026-05-23.zip` contains:

- `release_artifacts/validation_summary.json`
- `release_artifacts/toolathlon_artifact_build_summary.json`
- `release_artifacts/toolathlon_mcp_smoke_summary.json`
- `release_artifacts/toolathlon_preflight_summary.json`
- `release_artifacts/docker_mcp_smoke_summary.json`
- `release_artifacts/docker_preflight_summary.json`
- `release_artifacts/RELEASE_EVIDENCE_MANIFEST_2026-05-22.json`
- `release_artifacts/RELEASE_EVIDENCE_MANIFEST_2026-05-23.json`
- `release_artifacts/RELEASE_HANDOFF_2026-05-22.md`
- `release_artifacts/RELEASE_EVIDENCE_APPENDIX.md`
- `RELEASE_ATTESTATION_2026-05-22.md`

---

## Sign-off

This attestation confirms that the `pruned-smoke` release candidate at commit
`a0b34ab7f88906ef4699a5edb43b4d8d5c1ff153` has passed all required smoke-gate
validation checks and both archive artifacts are hash-bound to the evidence
recorded in `release_artifacts/RELEASE_EVIDENCE_MANIFEST_2026-05-23.json`.
