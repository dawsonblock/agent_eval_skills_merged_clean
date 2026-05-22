# Workspace Health Dashboard

**Date:** May 22, 2026  
**Scope:** agent_eval_skills_merged_clean  
**Classification:** Pruned smoke release candidate for controlled testing.
**Final clean archive SHA256:** `74b34edf25141c8f96bbf03975ed8e6675dd3f574d962be2921278295544b189`

This dashboard is an evidence tracker. It is not a release declaration.
All time-bound gate claims require fresh re-validation in the target environment before promotion.
If this dashboard is viewed from a distributed ZIP without accompanying evidence artifacts, treat status as release-candidate candidate.

Validation profiles:

1. `smoke` (default release-candidate gate)
2. `full` (experimental extended gate)

**Required evidence artifacts for release-candidate gate:**

- [.validation_logs/validation_summary.json](.validation_logs/validation_summary.json) — must have `overall_status = "passed"`
- [.validation_logs/toolathlon_artifact_build_summary.json](.validation_logs/toolathlon_artifact_build_summary.json) — must have `profile = smoke`, `overall_status = "passed"`, `package_count = expected_package_count`, `failed_count = 0`
- [.validation_logs/toolathlon_mcp_smoke_summary.json](.validation_logs/toolathlon_mcp_smoke_summary.json) — must have `profile = smoke`, `overall_status = "passed"`, and `failed_count = 0`
- [.validation_logs/toolathlon_preflight_summary.json](.validation_logs/toolathlon_preflight_summary.json) — must have `profile = smoke` and `missing_count = 0`
- [.validation_logs/docker_mcp_smoke_summary.json](.validation_logs/docker_mcp_smoke_summary.json) — required when claiming Docker proof
- [.validation_logs/](.validation_logs/) — phase logs for audit trail

## Current Status Table

```text
ZIP extraction ................ ✅ Verified
ZIP cache cleanliness ......... ✅ Verified
Python syntax ................. ✅ Verified
Agent Skills .................. ✅ Verified
ToolForge grouped validation .. ✅ Passed on supported Python
Toolathlon MCP smoke .......... ✅ Passed (`profile=smoke`, `passed_count=3`, `failed_count=0`)
Toolathlon fresh preflight .... ✅ Passed (`profile=smoke`, `missing_count=0`)
Toolathlon artifact builder ... ✅ Passed (`profile=smoke`, `package_count=3`, `expected_package_count=3`, `failed_count=0`)
Docker validation ............. ✅ Passed (`profile=smoke`, `target_count=3`, `failed_count=0`, checked_at=2026-05-22T08:50:15Z)
Unified validation ............ ✅ Passed (`overall_status=passed`, run_finished_at=2026-05-22T08:49:20Z)
Release readiness ............. ✅ Pruned smoke release candidate for controlled testing (hash-bound evidence attached)
```

## Promotion Rule

Release-candidate gate is satisfied **only when** the listed evidence artifacts show passing required gates for the target environment:

- `validation_summary.json`: `overall_status = "passed"`
- `toolathlon_artifact_build_summary.json`: `profile = smoke`, `overall_status = "passed"`, `package_count = expected_package_count`, `failed_count = 0`
- `toolathlon_mcp_smoke_summary.json`: `profile = smoke`, `overall_status = "passed"`, `failed_count = 0`, `passed_count = target_count`
- `toolathlon_preflight_summary.json`: `profile = smoke`, `missing_count = 0`
- `docker_mcp_smoke_summary.json`: `overall_status = "passed"` when Docker proof is claimed

Docker proof is optional for the default smoke gate and must only be claimed when generated in the same evidence run (or explicitly attached as external CI evidence).

The `full` profile remains available for extended validation but is not part of the default release-candidate gate until full evidence passes.

If any required summary artifact shows `profile != smoke` (or unified summary shows `capabilities.toolathlon_profile != smoke`), default release-candidate status is not met and evidence must be regenerated using the smoke validation entrypoint.

Production-grade claims remain out of scope pending separate hostile-code/runtime security audit.

## ⚠️ Dependency & Security Notes

- **npm vulnerabilities:** Local MCP servers report vulnerabilities and deprecations. Acceptable only for disposable containers and controlled dev labs.
- **Not hostile-code-safe:** Do not run on hosts with sensitive files or production data.
- **Out of scope:** Hostile-code isolation, dependency remediation, production security hardening.

## Evidence & Validation Notes

- Agent Skills and syntax hygiene are currently the strongest validated areas.
- ToolForge validation reports phase-level outcomes with stable logs in `.validation_logs/`.
- Runtime smoke proof is now part of the Toolathlon and Docker release gate because path existence alone does not prove Node/Python MCP entrypoints can start.
- **Gate enforcement:** If evidence artifacts are missing, stale, or indicate required gate failures, classification must be downgraded to strong repair candidate.
