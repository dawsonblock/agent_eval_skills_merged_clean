# Release Evidence Appendix (Pruned Smoke RC)

Date: 2026-05-22
Repository: agent_eval_skills_merged_clean
Branch: repair/pruned-release-candidate
Classification: Pruned smoke release candidate for controlled testing

## Scope

Validated scope:
- ToolForge
- Agent Skills
- Toolathlon smoke profile

Retained but not release-validated:
- Toolathlon full profile
- All 503 Toolathlon tasks
- Full MCP server benchmark set

## Canonical Evidence Files

- [.validation_logs/validation_summary.json](.validation_logs/validation_summary.json)
- [.validation_logs/toolathlon_artifact_build_summary.json](.validation_logs/toolathlon_artifact_build_summary.json)
- [.validation_logs/toolathlon_mcp_smoke_summary.json](.validation_logs/toolathlon_mcp_smoke_summary.json)
- [.validation_logs/toolathlon_preflight_summary.json](.validation_logs/toolathlon_preflight_summary.json)
- [.validation_logs/docker_mcp_smoke_summary.json](.validation_logs/docker_mcp_smoke_summary.json) (required only when Docker proof is claimed)
- [.validation_logs/docker_preflight_summary.json](.validation_logs/docker_preflight_summary.json) (required only when Docker proof is claimed)

## Evidence Snapshot

Unified workspace validation ([.validation_logs/validation_summary.json](.validation_logs/validation_summary.json)):
- overall_status: passed
- failed_phase_count: 0
- run_started_at: 2026-05-22T04:02:18Z
- run_finished_at: 2026-05-22T04:03:20Z
- capabilities.toolathlon_profile: smoke
- capabilities.rc_smoke_gate_enforced: true
- capabilities.docker_requested: true
- phase statuses: toolforge=passed, agent_skills=passed, toolathlon=passed, docker=passed

Toolathlon artifact summary ([.validation_logs/toolathlon_artifact_build_summary.json](.validation_logs/toolathlon_artifact_build_summary.json)):
- profile: smoke
- overall_status: passed
- expected_package_count: 3
- package_count: 3
- passed_count: 3
- failed_count: 0
- skip mode behavior: runtime_ready_skip observed for all 3 packages

Toolathlon runtime smoke ([.validation_logs/toolathlon_mcp_smoke_summary.json](.validation_logs/toolathlon_mcp_smoke_summary.json)):
- profile: smoke
- overall_status: passed
- target_count: 3
- passed_count: 3
- failed_count: 0
- checked_at: 2026-05-22T04:03:16Z

Toolathlon preflight ([.validation_logs/toolathlon_preflight_summary.json](.validation_logs/toolathlon_preflight_summary.json)):
- profile: smoke
- status: passed
- found_count: 3
- missing_count: 0
- checked_at: 2026-05-22T04:03:16.713519+00:00

Docker runtime smoke ([.validation_logs/docker_mcp_smoke_summary.json](.validation_logs/docker_mcp_smoke_summary.json)):
- profile: smoke
- overall_status: passed
- target_count: 3
- passed_count: 3
- failed_count: 0
- checked_at: 2026-05-22T04:03:19Z

Docker preflight ([.validation_logs/docker_preflight_summary.json](.validation_logs/docker_preflight_summary.json)):
- profile: smoke
- status: passed
- missing_count: 0
- found_count: 3
- checked_at: 2026-05-22T04:03:20.559687+00:00

Command used:

```bash
TOOLATHLON_PROFILE=smoke ENFORCE_RC_SMOKE_PROFILE=1 RUN_DOCKER=1 bash scripts/validate_workspace.sh
```

## Packaging Evidence

Clean release archive:
- [agent_eval_skills_merged_clean-pruned-smoke.zip](agent_eval_skills_merged_clean-pruned-smoke.zip)
- SHA256: 7753ee61fd84148e8ff2feb6a8214d120aef74411f827eaeb8c59aaa4333cdc0

Hygiene checks:
- Forbidden archive entries scan: no matches for __MACOSX, /._, .DS_Store, node_modules, .validation_logs, __pycache__, .pytest_cache, .mypy_cache, .ruff_cache, .venv
- Scratch extraction scan: no matches for __MACOSX, ._ files, .DS_Store, node_modules, .validation_logs, __pycache__, .pytest_cache

## Safety Statement

- Not production-grade.
- Not hostile-code-safe.
- Use disposable benchmark containers.
- Dependency/security audit required before broader deployment.
