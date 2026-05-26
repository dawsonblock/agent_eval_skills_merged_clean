# SkillForge Candidate Attestation

Date: 2026-05-25
Repository: agent_eval_skills_merged_clean
Branch: main
Commit: cc77d87ca59d2f664a8103f9f2859bccb0b23325

## Candidate Artifact Pair (Non-Canonical)

1. Candidate archive
   - Filename: `skillforge_ai_candidate_2026-05-25.zip`
   - Path: `dist/skillforge_ai_candidate_2026-05-25.zip`
   - SHA256: `de03fbf3bdfdf1c02485b35586a05fe8c3ea61a42109d9e696bf2a2e4a53ae83`

2. Candidate evidence bundle
   - Filename: `agent_eval_skills_merged_clean-skillforge-evidence-2026-05-25.zip`
   - Path: `dist/agent_eval_skills_merged_clean-skillforge-evidence-2026-05-25.zip`
   - SHA256: `3449b8d252198c6565e34bd77cdc0fbce3a847765eb960cbb5d47b366247d34f`

## Candidate Evidence Set

- `release_artifacts/skillforge_ai_test_summary.json`
- `release_artifacts/skillforge_ai_csv_cleaner_e2e_summary.json`
- `release_artifacts/skillforge_ai_validation_summary.json`
- `release_artifacts/skillforge_ai_candidate_build_summary.json`
- `release_artifacts/skillforge_ai_baseline_gate_summary.json`
- `release_artifacts/skillforge_ai_baseline_gate_2026-05-25.log`
- `release_artifacts/SKILLFORGE_CANDIDATE_MANIFEST_2026-05-25.json`

## Validation Outcomes

- SkillForge targeted tests: 181 passed, 0 failed
- csv-cleaner e2e lifecycle: passed
- csv-cleaner validation: passed (attempt 1)
- SkillForge baseline gate: passed (path, git parity, candidate hash, candidate hygiene, regression tests)

## Governance Constraint

This is a non-canonical SkillForge candidate attestation.

It does not supersede the canonical foundation release pair bound in:

- `RELEASE_ATTESTATION_2026-05-22.md`
- `RELEASE_EVIDENCE_MANIFEST_2026-05-22.json`

Any promotion beyond candidate status requires fresh policy approval and release labeling consistent with repository governance scripts.
