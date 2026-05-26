# Public Release Note

Date: 2026-05-22
Repository: agent_eval_skills_merged_clean
Release classification: Pruned smoke release candidate for controlled testing

## Canonical Release Artifacts

The release is defined by this exact artifact pair:

1. Release archive
   - Filename: agent_eval_skills_merged_clean-pruned-smoke.zip
   - SHA256: 9f206ffbdcfe83a2772579ea830c9124b930e6fae4240ee1817b2fac31616251

2. Evidence bundle
   - Filename: agent_eval_skills_merged_clean-smoke-evidence-2026-05-22.zip
   - SHA256: f365e50185cc1a37a0127c7c048a63e9ffb1a5e3aa755517bdaa45c5fd26f3c3

These values are hash-bound in the release attestation and evidence manifest.

## Artifact Identity Policy

Release-candidate status is bound to the exact canonical artifact pair and exact SHA256 values above.

Any wrapper/source bundle upload or regenerated ZIP with different bytes is out of scope for this release note and must be classified as unbound until a new manifest plus attestation explicitly rebinding to those new hashes is issued.

## Scope Covered By Attached Evidence

- ToolForge validation under Python 3.12
- Agent Skills validation (23 skills, 0 hard failures)
- Toolathlon smoke profile validation
  - Artifact build
  - MCP runtime smoke
  - MCP preflight path checks
- Docker smoke validation
  - MCP runtime smoke in container
  - MCP preflight path checks in container

## Accepted vs Not Accepted

Accepted:

- The exact artifact pair listed above, with exact SHA256 matches.

Not accepted under this release note:

- Wrapper/source ZIP uploads whose hash differs from the canonical release archive hash.
- Independently regenerated ZIPs with different byte-level output.
- Any archive or evidence bundle whose SHA256 does not match the canonical values above.

## Rejection Rule

If either artifact hash differs from the canonical value, classify the package as an unbound wrapper/source bundle (release-candidate candidate) until a new matching manifest + attestation pair is produced.

## Source Of Truth

- RELEASE_ATTESTATION_2026-05-22.md
- RELEASE_EVIDENCE_MANIFEST_2026-05-22.json
- release_artifacts/RELEASE_EVIDENCE_MANIFEST_2026-05-22.json
