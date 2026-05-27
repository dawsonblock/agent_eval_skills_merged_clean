# Release Handoff (2026-05-22)

Repository: agent_eval_skills_merged_clean
Branch: main
Commit: cebce44

## Current Label

Pruned smoke release candidate for controlled testing (local evidence bundle prepared for the matching archive hash).

Promotion label is permitted only when the matching machine-readable evidence bundle is published for the same archive hash.

## Upload Archive

- Archive: `agent_eval_skills_merged_clean-pruned-smoke.zip`
- SHA256: `88b4514aec9203910b85333a868d64437876b1f7127023bfb37ae2d324b06a43`
- Forbidden-entry scan: passed (`__MACOSX`, `._*`, `.DS_Store`, `node_modules`, `.validation_logs`, caches, `.venv` absent)

## Required Evidence Bundle (same build/hash)

- `.validation_logs/validation_summary.json`
- `.validation_logs/toolathlon_artifact_build_summary.json`
- `.validation_logs/toolathlon_mcp_smoke_summary.json`
- `.validation_logs/toolathlon_preflight_summary.json`
- `RELEASE_EVIDENCE_MANIFEST_2026-05-22.json`

## Gate Snapshot (from current local proof run)

- Unified validation: `overall_status=passed`, `failed_phase_count=0`
- Unified validation runtime: `python_version=3.12.12`
- Toolathlon smoke targets: `rail_12306`, `filesystem`
- Toolathlon artifact build: `profile=smoke`, `overall_status=passed`, `package_count=2`, `expected_package_count=2`, `failed_count=0`
- Toolathlon MCP smoke: `profile=smoke`, `overall_status=passed`, `target_count=2`, `passed_count=2`, `failed_count=0`
- Toolathlon preflight: `profile=smoke`, `status=passed`, `missing_count=0`

Google Calendar is optional/full-profile only and is not part of the required smoke gate.

## Promotion Rule

Promote to:

`agent_eval_skills_merged_clean — pruned smoke release candidate for controlled testing`

only when:

1. The uploaded archive hash matches this handoff.
2. The evidence files listed above are attached and readable.
3. Evidence values remain passing for smoke profile scope.

## Scope Statement

Validated scope:

- ToolForge
- Agent Skills
- Toolathlon smoke profile

Retained but not release-validated:

- Full Toolathlon profile
- all task material
- full MCP server set

## Safety Statement

- Not production-grade.
- Not hostile-code-safe.
- Use disposable benchmark containers.
- Run dependency/security audit before broader deployment.
