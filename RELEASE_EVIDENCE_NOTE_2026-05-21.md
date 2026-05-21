# Release Evidence Note (Pruned Smoke RC)

Date: 2026-05-21
Branch: repair/pruned-release-candidate
Repository: agent_eval_skills_merged_clean

## Verdict

Smoke release-candidate gate is satisfied for controlled testing.

## Unified Validation

Source: [.validation_logs/validation_summary.json](.validation_logs/validation_summary.json)

- overall_status: passed
- failed_phase_count: 0
- run_finished_at: 2026-05-21T23:03:42Z
- capabilities.toolathlon_profile: smoke
- capabilities.docker_requested: true
- capabilities.rc_smoke_gate_enforced: true

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
- checked_at: 2026-05-21T23:03:31Z

Preflight summary:
- profile: smoke
- status: passed
- missing_count: 0
- found_count: 3
- checked_at: 2026-05-21T23:03:31.477521+00:00

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
- checked_at: 2026-05-21T23:03:37Z

Docker preflight:
- profile: smoke
- status: passed
- missing_count: 0
- found_count: 3
- checked_at: 2026-05-21T23:03:41.530477+00:00

## Final Distributable ZIP

Source archive: [agent_eval_skills_merged_clean-pruned-smoke.zip](agent_eval_skills_merged_clean-pruned-smoke.zip)

- Forbidden-entry scan: no matches for __MACOSX, /._, .DS_Store, node_modules, .validation_logs, __pycache__, .pytest_cache, .mypy_cache, .ruff_cache, .venv
- SHA256: 42b6c456eead68b5850464cc4c9d24952240b0b2d817f339ee4918a117b990e3

## Scope Statement

Validated:
- ToolForge
- Agent Skills
- Toolathlon smoke profile
- Docker smoke + preflight

Retained but outside this gate:
- full Toolathlon profile (experimental, non-default)
- exhaustive benchmark claims beyond smoke gate
