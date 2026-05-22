# Release Evidence Note (Pruned Smoke RC)

Date: 2026-05-22
Branch: repair/pruned-release-candidate
Repository: agent_eval_skills_merged_clean

## Verdict

Smoke release candidate gate is satisfied for controlled testing.
Docker proof is included and passing in this unified run.

Environment:
- host OS: macOS
- Python: 3.12.9
- Docker: available (default context)

## Unified Validation

Source: [.validation_logs/validation_summary.json](.validation_logs/validation_summary.json)

- overall_status: passed
- failed_phase_count: 0
- run_finished_at: 2026-05-22T04:03:20Z
- capabilities.toolathlon_profile: smoke
- capabilities.docker_requested: true
- capabilities.rc_smoke_gate_enforced: true
- phase.docker.status: passed

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
- checked_at: 2026-05-22T04:03:16Z

Preflight summary:
- profile: smoke
- status: passed
- missing_count: 0
- found_count: 3
- checked_at: 2026-05-22T04:03:16.713519+00:00

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
- checked_at: 2026-05-22T04:03:19Z

Docker preflight:
- profile: smoke
- status: passed
- missing_count: 0
- found_count: 3
- checked_at: 2026-05-22T04:03:20.559687+00:00

Command used for this proof set:

```bash
TOOLATHLON_PROFILE=smoke ENFORCE_RC_SMOKE_PROFILE=1 RUN_DOCKER=1 bash scripts/validate_workspace.sh
```

## Final Distributable ZIP

Source archive: [agent_eval_skills_merged_clean-pruned-smoke.zip](agent_eval_skills_merged_clean-pruned-smoke.zip)

- Forbidden-entry scan: no matches for __MACOSX, /._, .DS_Store, node_modules, .validation_logs, __pycache__, .pytest_cache, .mypy_cache, .ruff_cache, .venv
- SHA256: 7753ee61fd84148e8ff2feb6a8214d120aef74411f827eaeb8c59aaa4333cdc0

## Scope Statement

Validated:
- ToolForge
- Agent Skills
- Toolathlon smoke profile
- Docker smoke + preflight

Retained but outside this gate:
- full Toolathlon profile (experimental, non-default)
- exhaustive benchmark claims beyond smoke gate
