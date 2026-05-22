# Release Evidence Note (Pruned Smoke RC)

Date: 2026-05-22
Branch: repair/pruned-release-candidate
Repository: agent_eval_skills_merged_clean

## Verdict

This note documents one specific unified validation run.
It does not, by itself, promote a new archive to release-candidate status unless the corresponding `.validation_logs` artifacts are attached for that same build.

Smoke release candidate gate is satisfied for controlled testing for the run documented below.
Docker proof is included and passing in that run.

Environment:
- host OS: macOS
- Python: 3.12.9
- Docker: available (default context)

## Unified Validation

Source: [.validation_logs/validation_summary.json](.validation_logs/validation_summary.json)

- overall_status: passed
- failed_phase_count: 0
- run_finished_at: 2026-05-22T04:41:08Z
- capabilities.toolathlon_profile: smoke
- capabilities.docker_requested: false
- capabilities.rc_smoke_gate_enforced: true
- phase.docker.status: skipped

## Toolathlon Smoke Proof

Sources:
- [.validation_logs/toolathlon_artifact_build_summary.json](.validation_logs/toolathlon_artifact_build_summary.json)
- [.validation_logs/toolathlon_mcp_smoke_summary.json](.validation_logs/toolathlon_mcp_smoke_summary.json)
- [.validation_logs/toolathlon_preflight_summary.json](.validation_logs/toolathlon_preflight_summary.json)

Artifact build summary:
- profile: smoke
- overall_status: passed
- expected_package_count: 3
- package_count: 3
- passed_count: 3
- failed_count: 0

MCP smoke summary:
- profile: smoke
- overall_status: passed
- target_count: 3
- passed_count: 3
- failed_count: 0
- checked_at: 2026-05-22T04:41:07Z

Preflight summary:
- profile: smoke
- status: passed
- missing_count: 0
- found_count: 3
- checked_at: 2026-05-22T04:41:08.330336+00:00

## Docker Proof

Sources:
- [.validation_logs/docker_mcp_smoke_summary.json](.validation_logs/docker_mcp_smoke_summary.json)
- [.validation_logs/docker_preflight_summary.json](.validation_logs/docker_preflight_summary.json)

Docker MCP smoke:
- profile: smoke
- overall_status: passed
- target_count: 3
- passed_count: 3
- failed_count: 0
- checked_at: 2026-05-22T04:41:24Z

Docker preflight:
- profile: smoke
- status: passed
- missing_count: 0
- found_count: 3
- checked_at: 2026-05-22T04:41:26.300281+00:00

Command used for this proof set:

```bash
bash scripts/validate_smoke_workspace.sh
TOOLATHLON_PROFILE=smoke bash toolathlon-gym-curated/scripts/validate_docker.sh
```

## Final Distributable ZIP

Source archive: [dist/agent_eval_skills_merged_clean-pruned-smoke-test.zip](dist/agent_eval_skills_merged_clean-pruned-smoke-test.zip)

- Forbidden-entry scan: no matches for __MACOSX, /._, .DS_Store, node_modules, .validation_logs, __pycache__, .pytest_cache, .mypy_cache, .ruff_cache, .venv
- SHA256: 1f6047e1709b7490545085f692ea455808b92565b978fe7fba7fa9fa527e61dc

## Scope Statement

Validated:
- ToolForge
- Agent Skills
- Toolathlon smoke profile
- Docker smoke + preflight

Retained but outside this gate:
- full Toolathlon profile (experimental, non-default)
- exhaustive benchmark claims beyond smoke gate
