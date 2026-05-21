# Validation Evidence

This document defines the minimum evidence required to claim release-candidate status for controlled testing.

## Required Artifacts

- `.validation_logs/validation_summary.json`
- `.validation_logs/toolathlon_preflight_summary.json`
- Phase logs in `.validation_logs/`

## Validation Commands

Run from repository root:

```bash
bash scripts/validate_workspace.sh
```

Run Docker proof when Docker is available:

```bash
cd toolathlon-gym-curated
docker build -t toolathlon:repair .
docker run --rm toolathlon:repair python scripts/preflight_mcp_paths.py --json-output /workspace/.validation_logs/toolathlon_preflight_summary.json
```

## Evidence Interpretation

`validation_summary.json` contains:

- `overall_status`
- `failed_phase_count`
- `capabilities` (Docker availability, Python support, requested modes)
- Per-phase status, duration, exit code, and log paths

`toolathlon_preflight_summary.json` contains:

- `found_count`
- `missing_count`
- `found` and `missing` path lists
- Timestamp and source directories

## Evidence State → Repo Status Mapping

| Evidence State | Repository Classification |
|---|---|
| `validation_summary.json` absent or stale | ❌ Strong repair candidate (not release-ready) |
| `validation_summary.json` overall_status = "failed" | ❌ Strong repair candidate (validation failed) |
| `toolathlon_preflight_summary.json` missing_count > 0 | ❌ Strong repair candidate (MCP paths missing) |
| `toolathlon_artifact_build_summary.json` failed_count > 0 | ❌ Strong repair candidate (artifact build failed) |
| Docker validation absent (RUN_DOCKER not set) | ⏸️ Docker-unverified (continue if host deployment only) |
| All required summaries pass + missing_count = 0 + failed_count = 0 | ✅ Release candidate for controlled testing |

## Promotion Rule

Claim release-candidate status only when:

1. All required artifacts are present and current:
   - `.validation_logs/validation_summary.json`
   - `.validation_logs/toolathlon_preflight_summary.json`
   - `.validation_logs/toolathlon_artifact_build_summary.json`
2. All required gates pass:
   - `validation_summary.json`: `overall_status = "passed"`
   - `toolathlon_preflight_summary.json`: `missing_count = 0` and `found_count = 26`
   - `toolathlon_artifact_build_summary.json`: `failed_count = 0` and `overall_status = "passed"`
3. Docker gate is either:
   - Proven in a Docker-capable environment (`docker_preflight_summary.json` with `missing_count = 0`), OR
   - Explicitly marked unavailable in the environment profile (set `RUN_DOCKER=0`)

If any condition is not met, classify as strong repair candidate.

## Dependency Risk & Security Scope

**This repository is not hostile-code-safe or production-grade.**

### Accepted Risk

- Local MCP server dependency trees contain npm packages with reported vulnerabilities and deprecation warnings.
- These are acceptable **only for disposable benchmark containers** and controlled developer environments.
- Do not run Toolathlon terminal, MCP, or agent workloads on host machines with sensitive files, credentials, or production data.

### Required Before Broader Distribution

1. Separate npm/Python dependency audit and remediation pass.
2. Hostile-code isolation assessment and hardening.
3. Runtime security review for production-grade claims.

This repository is suitable for:
- ✅ Local development and testing.
- ✅ Controlled benchmark environments in isolated containers.
- ✅ Evaluation labs under developer control.

This repository is NOT suitable for:
- ❌ Production application code without separate security audit.
- ❌ Untrusted code execution environments.
- ❌ Systems with sensitive data access.
- ❌ Cloud-facing deployments without hardening.
