# RC Smoke Release Gate Checklist

Date: 2026-05-21
Scope: Pruned smoke release candidate for controlled testing (hash-bound evidence attached)

This runbook defines the exact release gate for smoke profile promotion. Full Toolathlon profile remains retained but non-default and experimental.

Evidence publication rule:

- A release can be labeled release candidate only if required machine-readable summaries are attached as CI/release artifacts for that same build.
- Recommended artifact set:
  - `.validation_logs/validation_summary.json`
  - `.validation_logs/toolathlon_artifact_build_summary.json`
  - `.validation_logs/toolathlon_mcp_smoke_summary.json`
  - `.validation_logs/toolathlon_preflight_summary.json`
  - `.validation_logs/docker_mcp_smoke_summary.json` (when Docker proof is claimed)
  - `.validation_logs/docker_preflight_summary.json` (when Docker proof is claimed)

## 1) Profile Policy

- Default gate: `TOOLATHLON_PROFILE=smoke`
- Full profile (optional/experimental): `TOOLATHLON_PROFILE=full bash scripts/validate_full_workspace.sh`
- Validated smoke servers:
  - `rail_12306`
  - `filesystem`
  - `google_calendar`

## 2) Clean ZIP Packaging

Build:

```bash
bash scripts/create_release_zip.sh --output agent_eval_skills_merged_clean-pruned-smoke.zip
```

Verify forbidden entries absent:

```bash
unzip -l agent_eval_skills_merged_clean-pruned-smoke.zip | grep -E "__MACOSX|/\._|\.DS_Store|node_modules|\.validation_logs|__pycache__|\.pytest_cache|\.mypy_cache|\.ruff_cache|\.venv"
```

Expected: no output.

## 3) Toolathlon Smoke Build (fresh)

```bash
cd toolathlon-gym-curated
TOOLATHLON_PROFILE=smoke FORCE_REBUILD=1 bash scripts/build_required_mcp_artifacts.sh
```

Required summary values:

- `.validation_logs/toolathlon_artifact_build_summary.json`
  - `profile = smoke`
  - `overall_status = passed`
  - `expected_package_count = 3`
  - `package_count = 3`
  - `passed_count = 3`
  - `failed_count = 0`
- `.validation_logs/toolathlon_mcp_smoke_summary.json`
  - `profile = smoke`
  - `overall_status = passed`
  - `target_count = 3`
  - `passed_count = 3`
  - `failed_count = 0`
- `.validation_logs/toolathlon_preflight_summary.json`
  - `profile = smoke`
  - `status = passed`
  - `found_count = 3`
  - `missing_count = 0`

## 4) Toolathlon Repeatability (skip mode)

```bash
cd toolathlon-gym-curated
TOOLATHLON_PROFILE=smoke SKIP_EXISTING_ARTIFACTS=1 bash scripts/build_required_mcp_artifacts.sh
```

Required: still 3/3 packages, smoke pass, preflight `missing_count = 0`.

Automated strictness regression check (required before release promotion):

```bash
make verify-skip-strictness
```

Required outcomes:

- healthy skip run reports `runtime_ready_skip` for all three smoke targets
- unhealthy dependency perturbation forces rebuild with `filesystem` reason `rebuilt_after_npm_tree_unhealthy`

## 5) Unified Workspace Validation (Supported: Python 3.9-3.12; preferred release proof: 3.12)

```bash
python3.12 -m venv .venv
source .venv/bin/activate
bash scripts/validate_smoke_workspace.sh
```

If Python 3.12 is unavailable in a local environment, `python3` may be used for smoke checks as long as it resolves to Python 3.9-3.12. Release-candidate promotion evidence should be produced from a Python 3.12 run whenever possible.

Required in `.validation_logs/validation_summary.json`:

- `overall_status = passed`
- `failed_phase_count = 0`
- `capabilities.toolathlon_profile = smoke`
- `python_version` present (preferably `3.12.x` for promotion evidence)

## 6) ToolForge Direct Proof (targeted)

```bash
python3.12 -m venv .venv
source .venv/bin/activate
cd ToolForge
python -m pip install -e ".[dev]"
PYTHONPATH=. python -m apps.cli.toolforge_cli.main doctor
PYTHONPATH=. pytest -q tests/test_test_validator.py tests/integration/test_test_validator_subprocess.py
```

Required:

- Doctor passes
- Targeted validator tests pass

## 7) Agent Skills Proof

```bash
cd agent-skills-curated
node bin/cli.js list
node bin/cli.js eval --json
```

Required:

- 23 skills
- 0 hard failures
- 0 warnings
- valid JSON
- exit code 0

## 8) Docker Smoke Proof

```bash
cd toolathlon-gym-curated
TOOLATHLON_PROFILE=smoke bash scripts/validate_docker.sh
```

Required:

- `.validation_logs/docker_mcp_smoke_summary.json`
  - `profile = smoke`
  - `overall_status = passed`
  - `target_count = 3`
  - `passed_count = 3`
  - `failed_count = 0`
- `.validation_logs/docker_preflight_summary.json`
  - `profile = smoke`
  - `status = passed`
  - `missing_count = 0`

## 9) Extract-and-Revalidate Proof

```bash
rm -rf /tmp/agent_eval_smoke_final
unzip agent_eval_skills_merged_clean-pruned-smoke.zip -d /tmp/agent_eval_smoke_final
cd /tmp/agent_eval_smoke_final/<repo-folder>
python3.12 -m venv .venv
source .venv/bin/activate
bash scripts/validate_smoke_workspace.sh
```

Required: unified `overall_status = passed` from extracted archive run.

## 10) Final Label Rule

Apply release-candidate label only if all checks above pass and docs reflect smoke-only validated scope.

Final label text:

`agent_eval_skills_merged_clean — pruned smoke release candidate for controlled testing`

Validated scope:

- ToolForge
- Agent Skills
- Toolathlon smoke profile

Retained but not release-validated scope:

- Full Toolathlon profile
- all task material
- full MCP server set

## 11) Safety Statement (must remain)

- Not production-grade.
- Not hostile-code-safe.
- Use disposable benchmark containers.
- Run dependency/security audit before broader deployment.
