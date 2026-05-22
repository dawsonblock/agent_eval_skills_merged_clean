# Release Handoff (2026-05-22)

Repository: agent_eval_skills_merged_clean
Branch: repair/pruned-release-candidate
Commit: 5ae8912fc7a9d9310360ab2be9f3a838bff334ba

## Current Label

Pruned smoke release candidate for controlled testing (local evidence bundle prepared for the matching archive hash).

Promotion label is permitted only when the matching machine-readable evidence bundle is published for the same archive hash.

## Upload Archive

- Archive: `agent_eval_skills_merged_clean-pruned-smoke.zip`
- SHA256: `8211f984171eca17b26332a1fa4e4223719f2d95f391042ea86ecbc45ff92be1`
- Forbidden-entry scan: passed (`__MACOSX`, `._*`, `.DS_Store`, `node_modules`, `.validation_logs`, caches, `.venv` absent)

## Required Evidence Bundle (same build/hash)

- `.validation_logs/validation_summary.json`
- `.validation_logs/toolathlon_artifact_build_summary.json`
- `.validation_logs/toolathlon_mcp_smoke_summary.json`
- `.validation_logs/toolathlon_preflight_summary.json`
- `.validation_logs/docker_mcp_smoke_summary.json`
- `.validation_logs/docker_preflight_summary.json`
- `RELEASE_EVIDENCE_MANIFEST_2026-05-22.json`

## Gate Snapshot (from current local proof run)

- Unified validation: `overall_status=passed`, `failed_phase_count=0`
- Unified validation runtime: `python_version=3.12.9`
- Toolathlon artifact build: `profile=smoke`, `overall_status=passed`, `package_count=3`, `expected_package_count=3`, `failed_count=0`
- Toolathlon MCP smoke: `profile=smoke`, `overall_status=passed`, `target_count=3`, `passed_count=3`, `failed_count=0`
- Toolathlon preflight: `profile=smoke`, `status=passed`, `missing_count=0`
- Docker MCP smoke: `profile=smoke`, `overall_status=passed`, `failed_count=0`
- Docker preflight: `profile=smoke`, `status=passed`, `missing_count=0`

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

- Toolathlon full profile
- all 503 tasks
- full MCP server benchmark set

## Safety Statement

- Not production-grade.
- Not hostile-code-safe.
- Use disposable benchmark containers.
- Run dependency/security audit before broader deployment.
