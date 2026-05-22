# Phase 13 Acceptance Checklist

**Date:** May 21, 2026  
**Status:** Pruned smoke release candidate for controlled testing (smoke scope).

This checklist is a repair tracker and evidence log. Checkboxes do not imply release readiness unless all required gates pass from a fresh extraction.
All time-bound gate claims require fresh re-validation in the target environment before promotion.

Validation profiles:

1. `smoke` (default release-candidate gate)
2. `full` (experimental extended gate)

**Required evidence artifacts for release-candidate gate:**

- [.validation_logs/validation_summary.json](.validation_logs/validation_summary.json) — must have `overall_status = "passed"`
- [.validation_logs/toolathlon_artifact_build_summary.json](.validation_logs/toolathlon_artifact_build_summary.json) — must have `profile = smoke`, `failed_count = 0`, and `package_count = expected_package_count`
- [.validation_logs/toolathlon_mcp_smoke_summary.json](.validation_logs/toolathlon_mcp_smoke_summary.json) — must have `profile = smoke`, `overall_status = "passed"`, `failed_count = 0`, and `passed_count = target_count`
- [.validation_logs/toolathlon_preflight_summary.json](.validation_logs/toolathlon_preflight_summary.json) — must have `profile = smoke` and `missing_count = 0`
- [.validation_logs/](.validation_logs/) — phase logs for audit trail

## Required Gate Status

```text
ZIP extraction ................ ✅ Verified
ZIP cache cleanliness ......... ✅ Verified
Python syntax ................. ✅ Verified
Agent Skills .................. ✅ Verified
ToolForge grouped validation .. ✅ Passed on Python 3.12
Toolathlon fresh preflight .... ✅ Passed (`profile=smoke`, `missing_count=0`)
Toolathlon artifact builder ... ✅ Passed (`profile=smoke`, `package_count=3`, `expected_package_count=3`, `failed_count=0`)
Docker validation ............. ✅ Passed (`profile=smoke`, smoke + preflight, checked_at=2026-05-21T23:59:17Z)
Unified validation ............ ✅ Passed (`overall_status=passed`, run_finished_at=2026-05-21T23:59:03Z)
Release readiness ............. ✅ Smoke release-candidate gate satisfied
```

## Acceptance Gates

- [x] Repository can be cleaned with `scripts/clean_workspace.sh`.
- [x] Agent Skills inventory is present and evaluable.
- [x] Python source syntax can be checked cleanly.
- [x] ToolForge validation passes on supported Python with phase-group logs.
- [x] Toolathlon artifact build completes deterministically.
- [x] Toolathlon preflight passes immediately after artifact build.
- [x] Docker build uses one canonical context and fails honestly on required build failure.
- [x] Docker preflight passes inside container.
- [x] Unified validation passes end-to-end from a fresh extraction.

## Release Promotion Rule

Promotion gate is met **only when** required evidence artifacts show passing required gates for the target environment:

- `validation_summary.json`: `overall_status = "passed"`
- `toolathlon_artifact_build_summary.json`: `profile = smoke`, `failed_count = 0`, and `overall_status = "passed"`
- `toolathlon_mcp_smoke_summary.json`: `profile = smoke`, `overall_status = "passed"`, `failed_count = 0`, and `passed_count = target_count`
- `toolathlon_preflight_summary.json`: `profile = smoke` and `missing_count = 0`

**Smoke-scope release-candidate gate is satisfied for controlled testing based on fresh required artifacts for this environment. Full profile remains optional/experimental and is not implied by this checklist. This is not a production security attestation.**

### ⚠️ Security Disclaimer

Local MCP servers contain npm packages with reported vulnerabilities. These are acceptable only for disposable benchmark containers in controlled environments. Do not run on production hosts or systems with sensitive data. Hostile-code isolation and security hardening remain out of scope. A separate dependency audit is required before broader distribution.
