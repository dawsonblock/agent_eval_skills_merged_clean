# Claims Matrix

| Claim | Allowed wording | Evidence file | Status |
|-------|----------------|---------------|--------|
| Release hash verified | Canonical release ZIP hash matches lock | release_lock.json, SHA256SUMS.txt | Pass |
| Evidence hash verified | Evidence ZIP hash matches lock | release_lock.json, SHA256SUMS.txt | Pass |
| Source hygiene clean | Canonical release ZIP passes source bundle hygiene | verify_source_bundle_hygiene.sh | Pass |
| ToolForge tests | ToolForge test suite passed (371 passed, 6 warnings) | .validation_logs/test_results_toolforge.txt | Pass |
| Agent skills packages | 23 package ZIPs validate structurally | agent_skills_package_validation.json | Pass |
| Toolathlon smoke | 2-server smoke profile passed (rail_12306, filesystem) | toolathlon_smoke.json | Pass |
| Full Toolathlon | Not validated | none | Not claimed |
| Production security | Not audited | none | Not claimed |
| Hostile-code safety | Not proven | none | Not claimed |
| All skills high quality | Not all skills scored ≥70 | agent_skills_summary.json | Not claimed |
| npm vulnerabilities | Known vulnerabilities documented | docs/npm-vulnerability-report.md | Documented |
| Sandbox isolation | Sandbox profile defined, levels 0–4 available | sandbox_profile.json | Defined |
| Secret scan | No real secrets detected in workspace | check_for_real_secrets.py | Pass |
| Absolute path scan | No local path leaks in artifacts | check_no_absolute_local_paths.py | Pass |
| Policy drift | No release-policy drift in docs | validate_release_policy_drift.sh | Pass |

## Positioning Statement

This repository is a **canonical smoke release** for local ToolForge / SkillForge / Agent Skills / Toolathlon smoke validation.

- It is **not** production security-audited.
- It does **not** validate the full Toolathlon task corpus (504 tasks, 25 MCP configs).
- It does **not** prove hostile-code sandbox safety.
- It does **not** certify all 23 skills as high-quality; it validates package structure and known smoke evidence.

The release-gated Toolathlon smoke profile is limited to `rail_12306` and `filesystem` (import/build/start level). Google Calendar remains optional/full-profile only.

Weak or unscored skills (brand-guidelines: 25, theme-factory: 43, canvas-design: 47) are explicitly labeled experimental.
