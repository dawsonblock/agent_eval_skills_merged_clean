# Release Attestation

Date: 2026-05-22
Repository: agent_eval_skills_merged_clean
Branch: main
Commit: cd757b1

## Accepted Release Artifacts

1. Release archive
   - Filename: `agent_eval_skills_merged_clean-pruned-smoke.zip`
   - SHA256: `74b34edf25141c8f96bbf03975ed8e6675dd3f574d962be2921278295544b189`

2. Evidence bundle
   - Filename: `agent_eval_skills_merged_clean-smoke-evidence-2026-05-22.zip`
   - SHA256: `5d2e43a0d6e961f99209fab0c55e3c11c5795228200974315f44bdb5e608426c`

## Source Of Truth

- Manifest: `RELEASE_EVIDENCE_MANIFEST_2026-05-22.json`
  - `archive.path`: `agent_eval_skills_merged_clean-pruned-smoke.zip`
  - `archive_sha256`: `74b34edf25141c8f96bbf03975ed8e6675dd3f574d962be2921278295544b189`
  - `status_policy.current_label`: `Pruned smoke release candidate for controlled testing`

## Acceptance Rule

Only the release ZIP and evidence ZIP matching the exact SHA256 values above are accepted for this attestation.

Any other archive hash (including wrapper ZIP uploads or independently regenerated ZIPs with different bytes) is out of scope for this attestation and must be treated as unbound until a new matching evidence manifest and attestation are produced.

## Validation Scope Covered By Attached Evidence

- ToolForge validation under Python 3.12
- Agent Skills structural/eval validation
- Toolathlon smoke artifact build, runtime smoke, and preflight checks
- Docker smoke runtime and Docker preflight checks
