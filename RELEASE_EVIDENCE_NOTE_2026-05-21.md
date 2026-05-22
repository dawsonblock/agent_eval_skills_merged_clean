# Release Evidence Note (Pruned Smoke RC)

Date: 2026-05-22
Branch: repair/pruned-release-candidate
Repository: agent_eval_skills_merged_clean

## Verdict

This note documents one specific unified validation run.
It does not, by itself, promote a new archive to release-candidate status unless the corresponding `.validation_logs` artifacts are attached for that same build.

Smoke release candidate gate is satisfied for controlled testing for the run documented below.
Docker proof is included and passing as a paired evidence set for the same archive hash.

Environment:
- host OS: macOS
- Python: 3.12.9
- Docker: available (default context)

## Unified Validation

Source: [.validation_logs/validation_summary.json](.validation_logs/validation_summary.json)

- overall_status: passed
- failed_phase_count: 0
- run_finished_at: 2026-05-22T07:27:12Z
- capabilities.toolathlon_profile: smoke
- capabilities.docker_requested: false
- capabilities.rc_smoke_gate_enforced: true
- phase.docker.status: skipped (Docker proof captured separately below)

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
- checked_at: 2026-05-22T07:27:11Z

Preflight summary:
- profile: smoke
- status: passed
- missing_count: 0
- found_count: 3
- checked_at: 2026-05-22T07:27:11.978233+00:00

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
- checked_at: 2026-05-22T07:27:14Z

Docker preflight:
- profile: smoke
- status: passed
- missing_count: 0
- found_count: 3
- checked_at: 2026-05-22T07:27:15.287689+00:00

Command used for this proof set:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
bash scripts/validate_smoke_workspace.sh

cd toolathlon-gym-curated
TOOLATHLON_PROFILE=smoke bash scripts/validate_docker.sh

cd ToolForge
PYTHONPATH=. python -m apps.cli.toolforge_cli.main doctor
PYTHONPATH=. pytest -q tests/test_test_validator.py tests/integration/test_test_validator_subprocess.py

cd ../agent-skills-curated
node bin/cli.js list
node bin/cli.js eval --json

cd ../toolathlon-gym-curated
TOOLATHLON_PROFILE=smoke FORCE_REBUILD=1 bash scripts/build_required_mcp_artifacts.sh
TOOLATHLON_PROFILE=smoke SKIP_EXISTING_ARTIFACTS=1 bash scripts/build_required_mcp_artifacts.sh

cd ..
bash scripts/create_release_zip.sh --output agent_eval_skills_merged_clean-pruned-smoke.zip
```

## Final Distributable ZIP

Source archive: [agent_eval_skills_merged_clean-pruned-smoke.zip](agent_eval_skills_merged_clean-pruned-smoke.zip)

- Forbidden-entry scan: no matches for __MACOSX, /._, .DS_Store, node_modules, .validation_logs, __pycache__, .pytest_cache, .mypy_cache, .ruff_cache, .venv
- SHA256: 3402c2793c7125ef123b14596cf1390eb06023b4b843bcb0197e239e7bd8f6ce

## Scope Statement

Validated:
- ToolForge
- Agent Skills
- Toolathlon smoke profile
- Docker smoke + preflight

Retained but outside this gate:
- full Toolathlon profile (experimental, non-default)
- exhaustive benchmark claims beyond smoke gate
