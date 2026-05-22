# Validation Evidence

This document defines the minimum evidence required to claim release candidate status for controlled testing.

Current status (May 22, 2026): pruned smoke release candidate for controlled testing with matching machine-readable evidence attached for archive hash `74b34edf25141c8f96bbf03975ed8e6675dd3f574d962be2921278295544b189`.

Scope warning: status and promotion rules apply to `TOOLATHLON_PROFILE=smoke` only. Full profile remains optional/experimental unless separate full-profile evidence is presented.

Validation profiles:

1. `smoke` — default release-candidate gate
2. `full` — expanded MCP validation gate (experimental, non-default; currently 12 MCP artifact/runtime targets)

## Required Artifacts

- `.validation_logs/validation_summary.json`
- `.validation_logs/toolathlon_artifact_build_summary.json`
- `.validation_logs/toolathlon_mcp_smoke_summary.json`
- `.validation_logs/toolathlon_preflight_summary.json`
- Phase logs in `.validation_logs/`

## Validation Commands

Run from repository root:

```bash
bash scripts/validate_smoke_workspace.sh
```

Equivalent explicit invocation:

```bash
TOOLATHLON_PROFILE=smoke bash scripts/validate_workspace.sh
```

The canonical smoke release-candidate command enables strict gate scope enforcement:

```bash
bash scripts/validate_smoke_workspace.sh
```

This wrapper sets `ENFORCE_RC_SMOKE_PROFILE=1`, which fails fast if `TOOLATHLON_PROFILE` is not `smoke`.

Run extended full profile (experimental):

```bash
bash scripts/validate_full_workspace.sh
```

Run Docker proof when Docker is available:

```bash
DOCKER_CONTEXT=default bash toolathlon-gym-curated/scripts/validate_docker.sh
```

If your environment uses a non-default Docker context, set it explicitly:

```bash
DOCKER_CONTEXT=<your-context> bash toolathlon-gym-curated/scripts/validate_docker.sh
```

Docker proof is conditional and should only be claimed when the Docker summaries from the same run are published.

## CI Behavior

The repository CI workflow enforces `smoke` profile validation for default push and pull-request gates.

An experimental `full` profile validation job is available via scheduled and manual workflow runs. That full-profile job is non-blocking and is intended for extended evidence collection, not default release gating.

Task profile manifests are retained for future expansion, but current gate scripts only enforce profile-aware MCP artifact/runtime/preflight scope.

## Evidence Interpretation

`validation_summary.json` contains:

- `python_version` and `python_executable`
- `overall_status`
- `failed_phase_count`
- `capabilities` (Docker availability, Python support, requested modes)
- Per-phase status, duration, exit code, and log paths

`toolathlon_preflight_summary.json` contains:

- `status` (`"passed"` when `missing_count = 0`, else `"failed"`)
- `found_count`
- `missing_count`
- `found` and `missing` path lists
- Timestamp and source directories

`toolathlon_mcp_smoke_summary.json` contains:

- `profile`
- `overall_status`
- `target_count`
- `passed_count`
- `failed_count`
- Per-target runtime/import smoke results for the required artifact-producing MCP servers

## Evidence State → Repo Status Mapping

| Evidence State | Repository Classification |
| --- | --- |
| `validation_summary.json` absent or stale | ❌ Strong repair candidate (not release-ready) |
| `validation_summary.json` overall_status = "failed" | ❌ Strong repair candidate (validation failed) |
| `toolathlon_mcp_smoke_summary.json` missing or failed | ❌ Strong repair candidate (runtime smoke proof missing) |
| `toolathlon_preflight_summary.json` missing_count > 0 | ❌ Strong repair candidate (MCP paths missing) |
| `toolathlon_artifact_build_summary.json` failed_count > 0 or package_count != expected_package_count | ❌ Strong repair candidate (artifact build failed or incomplete) |
| Any required summary has `profile != smoke` for release-candidate claim | ❌ Strong repair candidate (wrong gate scope) |
| Docker validation absent (RUN_DOCKER not set) | ⏸️ Docker-unverified (continue if host deployment only) |
| All required summaries pass + smoke passes + missing_count = 0 + failed_count = 0 | ✅ Release candidate for controlled testing |

## Promotion Rule

Claim release-candidate status only when:

1. All required artifacts are present and current:
   - `.validation_logs/validation_summary.json`
   - `.validation_logs/toolathlon_preflight_summary.json`
   - `.validation_logs/toolathlon_artifact_build_summary.json`
   - `.validation_logs/toolathlon_mcp_smoke_summary.json`
2. All required gates pass:
   - `validation_summary.json`: `overall_status = "passed"`
   - `toolathlon_artifact_build_summary.json`: `profile = "smoke"`, `overall_status = "passed"`, `package_count = expected_package_count`, `passed_count = expected_package_count`, `failed_count = 0`
   - `toolathlon_mcp_smoke_summary.json`: `profile = "smoke"`, `overall_status = "passed"`, `failed_count = 0`, and `passed_count = target_count`
   - `toolathlon_preflight_summary.json`: `profile = "smoke"` and `missing_count = 0`
3. Docker gate is either:
   - Proven in a Docker-capable environment (`docker_mcp_smoke_summary.json` with `overall_status = "passed"` and `docker_preflight_summary.json` with `missing_count = 0`), OR
   - Explicitly marked unavailable in the environment profile (set `RUN_DOCKER=0`)

If any condition is not met, classify as strong repair candidate.

If evidence exists from a prior run but is not published with the current candidate build, keep the label at release-candidate candidate.

If evidence was generated with `TOOLATHLON_PROFILE=full`, regenerate smoke evidence before making a default release-candidate claim:

```bash
bash scripts/validate_smoke_workspace.sh
```

`full` profile evidence can be collected for expanded validation but does not override smoke-gate requirements for release-candidate status.

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
