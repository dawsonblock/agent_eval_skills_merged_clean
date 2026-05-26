# Release Evidence Appendix (Pruned Smoke RC)

Date: 2026-05-22
Repository: agent_eval_skills_merged_clean
Branch: main
Classification: Pruned smoke release candidate for controlled testing

Applies only to the canonical attested pair:

- `agent_eval_skills_merged_clean-pruned-smoke.zip`
	- SHA256: `2918ecd852deae6fa49dee983d39d9882db175d8817eed42a5162c6e4c8fd231`
- `agent_eval_skills_merged_clean-smoke-evidence-2026-05-22.zip`
	- SHA256: `959cb033495fa5c04575743bfc6d262a72a6275b3f2dafadace216f80acfb526`

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
- SHA256: 2918ecd852deae6fa49dee983d39d9882db175d8817eed42a5162c6e4c8fd231

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

- Candidate archive:
	- `dist/skillforge_ai_candidate_2026-05-25.zip`
	- SHA256: `de03fbf3bdfdf1c02485b35586a05fe8c3ea61a42109d9e696bf2a2e4a53ae83`
- Candidate evidence bundle:
	- `dist/agent_eval_skills_merged_clean-skillforge-evidence-2026-05-25.zip`
	- SHA256: `3449b8d252198c6565e34bd77cdc0fbce3a847765eb960cbb5d47b366247d34f`
- [release_artifacts/skillforge_ai_test_summary.json](release_artifacts/skillforge_ai_test_summary.json)
- [release_artifacts/skillforge_ai_csv_cleaner_e2e_summary.json](release_artifacts/skillforge_ai_csv_cleaner_e2e_summary.json)
- [release_artifacts/skillforge_ai_validation_summary.json](release_artifacts/skillforge_ai_validation_summary.json)
- [release_artifacts/skillforge_ai_candidate_build_summary.json](release_artifacts/skillforge_ai_candidate_build_summary.json)
- [release_artifacts/skillforge_ai_baseline_gate_summary.json](release_artifacts/skillforge_ai_baseline_gate_summary.json)
- [release_artifacts/skillforge_ai_baseline_gate_2026-05-25.log](release_artifacts/skillforge_ai_baseline_gate_2026-05-25.log)
- [release_artifacts/SKILLFORGE_CANDIDATE_MANIFEST_2026-05-25.json](release_artifacts/SKILLFORGE_CANDIDATE_MANIFEST_2026-05-25.json)
- [SKILLFORGE_CANDIDATE_ATTESTATION_2026-05-25.md](SKILLFORGE_CANDIDATE_ATTESTATION_2026-05-25.md)

Generate or refresh these artifacts with:

```bash
bash scripts/generate_skillforge_ai_summaries.sh
bash scripts/build_skillforge_ai_candidate_zip.sh
bash scripts/create_skillforge_evidence_bundle.sh --date 20260525 --output dist/agent_eval_skills_merged_clean-skillforge-evidence-2026-05-25.zip
```

Current run status (2026-05-26 UTC):

- SkillForge targeted tests: 181 passed, 0 failed
- csv-cleaner e2e lifecycle: passed in isolated temp workspace
- csv-cleaner validation summary: passed
- baseline gate: passed (path/git parity/hash/hygiene/regression tests)
- Candidate and evidence ZIP hygiene validation: passed (no forbidden entries)
