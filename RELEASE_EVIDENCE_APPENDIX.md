# Release Evidence Appendix (Pruned Smoke RC)

Date: 2026-05-22
Repository: agent_eval_skills_merged_clean
Branch: main
Classification: Pruned smoke release candidate for controlled testing

Applies only to the canonical attested pair:

- `agent_eval_skills_merged_clean-pruned-smoke.zip`
	- SHA256: `74b34edf25141c8f96bbf03975ed8e6675dd3f574d962be2921278295544b189`
- `agent_eval_skills_merged_clean-smoke-evidence-2026-05-22.zip`
	- SHA256: `5d2e43a0d6e961f99209fab0c55e3c11c5795228200974315f44bdb5e608426c`

Wrapper/source ZIP uploads and independently regenerated ZIPs are not the attested release unless their hashes match the attestation.

## Scope

Promotion label (only when this evidence bundle is attached for the same archive hash):

- Pruned smoke release candidate for controlled testing

Validated scope:

- ToolForge
- Agent Skills
- Toolathlon smoke profile

Retained but not release-validated:

- Full Toolathlon profile
- all task material
- full MCP server set

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
- run_started_at: 2026-05-22T08:48:31Z
- run_finished_at: 2026-05-22T08:49:20Z
- python_version: 3.12.9
- capabilities.toolathlon_profile: smoke
- capabilities.rc_smoke_gate_enforced: true
- capabilities.docker_requested: false
- phase statuses: toolforge=passed, agent_skills=passed, toolathlon=passed, docker=skipped (separate docker proof captured below)

Toolathlon artifact summary ([.validation_logs/toolathlon_artifact_build_summary.json](.validation_logs/toolathlon_artifact_build_summary.json)):

- profile: smoke
- overall_status: passed
- expected_package_count: 3
- package_count: 3
- passed_count: 3
- failed_count: 0
- skip mode behavior: runtime_ready_skip observed for all 3 packages
- partial dependency negative test: deleting `filesystem/node_modules/@modelcontextprotocol/sdk` forced rebuild with reason `rebuilt_after_npm_tree_unhealthy` (skip was correctly rejected)

Toolathlon runtime smoke ([.validation_logs/toolathlon_mcp_smoke_summary.json](.validation_logs/toolathlon_mcp_smoke_summary.json)):

- profile: smoke
- overall_status: passed
- target_count: 3
- passed_count: 3
- failed_count: 0
- checked_at: 2026-05-22T08:49:20Z

Toolathlon preflight ([.validation_logs/toolathlon_preflight_summary.json](.validation_logs/toolathlon_preflight_summary.json)):

- profile: smoke
- status: passed
- found_count: 3
- missing_count: 0
- checked_at: 2026-05-22T08:50:02.167768+00:00

Docker runtime smoke ([.validation_logs/docker_mcp_smoke_summary.json](.validation_logs/docker_mcp_smoke_summary.json)):

- profile: smoke
- overall_status: passed
- target_count: 3
- passed_count: 3
- failed_count: 0
- checked_at: 2026-05-22T08:50:15Z

Docker preflight ([.validation_logs/docker_preflight_summary.json](.validation_logs/docker_preflight_summary.json)):

- profile: smoke
- status: passed
- missing_count: 0
- found_count: 3
- checked_at: 2026-05-22T08:50:16.579941+00:00

Smoke command used:

```bash
bash scripts/validate_smoke_workspace.sh
```

Docker command used:

```bash
cd toolathlon-gym-curated
TOOLATHLON_PROFILE=smoke bash scripts/validate_docker.sh
```

Direct proof commands executed in this cycle:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
bash scripts/validate_smoke_workspace.sh

cd toolathlon-gym-curated
TOOLATHLON_PROFILE=smoke bash scripts/validate_docker.sh

cd ..
bash scripts/create_release_zip.sh --output agent_eval_skills_merged_clean-pruned-smoke.zip
```

## Packaging Evidence

Clean release archive:

- [agent_eval_skills_merged_clean-pruned-smoke.zip](agent_eval_skills_merged_clean-pruned-smoke.zip)
- SHA256: 74b34edf25141c8f96bbf03975ed8e6675dd3f574d962be2921278295544b189

Hygiene checks:

- Forbidden archive entries scan: no matches for __MACOSX, /._, .DS_Store, node_modules, .validation_logs, __pycache__, .pytest_cache, .mypy_cache, .ruff_cache, .venv
- Scratch extraction scan: no matches for __MACOSX, ._ files, .DS_Store, node_modules, .validation_logs, __pycache__, .pytest_cache

## Safety Statement

- Not production-grade.
- Not hostile-code-safe.
- Use disposable benchmark containers.
- Dependency/security audit required before broader deployment.

## SkillForge Candidate Evidence (Non-Canonical)

The following artifacts support SkillForge AI candidate claims and are separate from the canonical 2026-05-22 release/evidence pair:

- [release_artifacts/skillforge_ai_test_summary.json](release_artifacts/skillforge_ai_test_summary.json)
- [release_artifacts/skillforge_ai_csv_cleaner_e2e_summary.json](release_artifacts/skillforge_ai_csv_cleaner_e2e_summary.json)
- [release_artifacts/skillforge_ai_validation_summary.json](release_artifacts/skillforge_ai_validation_summary.json)

Generate or refresh these artifacts with:

```bash
bash scripts/generate_skillforge_ai_summaries.sh
```
