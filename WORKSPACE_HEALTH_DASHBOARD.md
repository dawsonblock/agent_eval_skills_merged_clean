# Workspace Health Dashboard

**Date:** May 20, 2026  
**Scope:** agent_eval_skills_merged_clean  
**Classification:** Evidence-gated. Treat as strong repair candidate until all required artifacts are freshly regenerated and passing.

This dashboard is an evidence tracker. It is not a release declaration.

**Required evidence artifacts for release-candidate gate:**

- [.validation_logs/validation_summary.json](.validation_logs/validation_summary.json) — must have `overall_status = "passed"`
- [.validation_logs/toolathlon_artifact_build_summary.json](.validation_logs/toolathlon_artifact_build_summary.json) — must have `overall_status = "passed"`, `expected_package_count = 12`, `package_count = 12`, `passed_count = 12`, `failed_count = 0`
- [.validation_logs/toolathlon_mcp_smoke_summary.json](.validation_logs/toolathlon_mcp_smoke_summary.json) — must have `overall_status = "passed"` and `failed_count = 0`
- [.validation_logs/toolathlon_preflight_summary.json](.validation_logs/toolathlon_preflight_summary.json) — must have `missing_count = 0` and `found_count = 26`
- [.validation_logs/docker_mcp_smoke_summary.json](.validation_logs/docker_mcp_smoke_summary.json) — required when claiming Docker proof
- [.validation_logs/](.validation_logs/) — phase logs for audit trail

## Current Status Table

```text
ZIP extraction ................ ✅ Verified
ZIP cache cleanliness ......... ✅ Verified
Python syntax ................. ✅ Verified
Agent Skills .................. ✅ Verified
ToolForge doctor .............. 🟡 Passes after dependency setup
ToolForge full validation ..... ⚪ Requires fresh supported-Python proof
Toolathlon MCP smoke .......... ⚪ Requires fresh host runtime smoke proof
Toolathlon fresh preflight .... ⚪ Requires fresh post-build Missing: 0 proof
Toolathlon artifact builder ... ⚪ Requires summary gate pass (`overall_status=passed`, `failed_count=0`, `package_count=expected_package_count`)
Docker validation ............. ⚪ Requires fresh Docker-host smoke + preflight proof
Unified validation ............ ⚪ Requires fresh end-to-end passing run
Release readiness ............. ⚪ Conditional on required evidence gates
```

## Promotion Rule

Release-candidate gate is satisfied **only when** the listed evidence artifacts show passing required gates for the target environment:

- `validation_summary.json`: `overall_status = "passed"`
- `toolathlon_artifact_build_summary.json`: `overall_status = "passed"`, `expected_package_count = 12`, `package_count = 12`, `passed_count = 12`, `failed_count = 0`
- `toolathlon_mcp_smoke_summary.json`: `overall_status = "passed"`, `failed_count = 0`, `passed_count = target_count`
- `toolathlon_preflight_summary.json`: `missing_count = 0` and `found_count = 26`
- `docker_mcp_smoke_summary.json`: `overall_status = "passed"` when Docker proof is claimed

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
