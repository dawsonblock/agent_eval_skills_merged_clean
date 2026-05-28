# Release Attestation

Date: 2026-05-22
Repository: agent_eval_skills_merged_clean
Branch: main
Commit: cebce44

## Accepted Release Artifacts

1. Release archive
   - Filename: `agent_eval_skills_merged_clean-pruned-smoke.zip`
   - SHA256: `88b4514aec9203910b85333a868d64437876b1f7127023bfb37ae2d324b06a43`

2. Evidence bundle
   - Filename: `agent_eval_skills_merged_clean-smoke-evidence-2026-05-22.zip`
   - SHA256: `34c8da07a487aef1fc69fb74d609de427d2e673ed999c5f29fa2de7d5f9bb79a`

## Source Of Truth

- Manifest: `RELEASE_EVIDENCE_MANIFEST_2026-05-22.json`
- `release_zip`: `agent_eval_skills_merged_clean-pruned-smoke.zip`
- `release_zip_sha256`: `88b4514aec9203910b85333a868d64437876b1f7127023bfb37ae2d324b06a43`
- `evidence_zip`: `agent_eval_skills_merged_clean-smoke-evidence-2026-05-22.zip`
- `evidence_zip_sha256`: `34c8da07a487aef1fc69fb74d609de427d2e673ed999c5f29fa2de7d5f9bb79a`
- `archive.path`: `agent_eval_skills_merged_clean-pruned-smoke.zip`
- `archive_sha256`: `88b4514aec9203910b85333a868d64437876b1f7127023bfb37ae2d324b06a43`
- `status_policy.current_label`: `Pruned smoke release candidate for controlled testing`

## Acceptance Rule

Only the release ZIP and evidence ZIP matching the exact SHA256 values above are accepted for this attestation.

Any other archive hash (including wrapper ZIP uploads or independently regenerated ZIPs with different bytes) is out of scope for this attestation and must be treated as unbound until a new matching evidence manifest and attestation are produced.

## Validation Scope Covered By Attached Evidence

- ToolForge validation under Python 3.12
- Agent Skills structural/eval validation
- Toolathlon smoke artifact build, runtime smoke, and preflight checks
- Required smoke targets: `rail_12306`, `filesystem`
- `google_calendar` retained as optional/full-profile only
