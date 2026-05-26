# Release Attestation

Date: 2026-05-22
Repository: agent_eval_skills_merged_clean
Branch: main
Commit: cd757b1

## Accepted Release Artifacts

1. Release archive
   - Filename: `agent_eval_skills_merged_clean-pruned-smoke.zip`
   - SHA256: `4d934a0bd6976d9918201dd8a616e599be827268014cae7853192f62b134e027`

2. Evidence bundle
   - Filename: `agent_eval_skills_merged_clean-smoke-evidence-2026-05-22.zip`
   - SHA256: `f03be73880cdbce0d21eec5d70acd6c0c0990f0c1b1f491ed7439e28a95dde7a`

## Source Of Truth

- Manifest: `RELEASE_EVIDENCE_MANIFEST_2026-05-22.json`
   - `release_zip`: `agent_eval_skills_merged_clean-pruned-smoke.zip`
   - `release_zip_sha256`: `4d934a0bd6976d9918201dd8a616e599be827268014cae7853192f62b134e027`
   - `evidence_zip`: `agent_eval_skills_merged_clean-smoke-evidence-2026-05-22.zip`
   - `evidence_zip_sha256`: `f03be73880cdbce0d21eec5d70acd6c0c0990f0c1b1f491ed7439e28a95dde7a`
  - `archive.path`: `agent_eval_skills_merged_clean-pruned-smoke.zip`
  - `archive_sha256`: `4d934a0bd6976d9918201dd8a616e599be827268014cae7853192f62b134e027`
  - `status_policy.current_label`: `Pruned smoke release candidate for controlled testing`

## Acceptance Rule

Only the release ZIP and evidence ZIP matching the exact SHA256 values above are accepted for this attestation.

Any other archive hash (including wrapper ZIP uploads or independently regenerated ZIPs with different bytes) is out of scope for this attestation and must be treated as unbound until a new matching evidence manifest and attestation are produced.

## Validation Scope Covered By Attached Evidence

- ToolForge validation under Python 3.12
- Agent Skills structural/eval validation
- Toolathlon smoke artifact build, runtime smoke, and preflight checks
- Docker smoke runtime and Docker preflight checks
