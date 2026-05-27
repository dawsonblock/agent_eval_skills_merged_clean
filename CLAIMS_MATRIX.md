# Claims Matrix

| Claim | Allowed now? | Required proof |
| --- | --- | --- |
| ToolForge core tests pass | Yes | ToolForge pytest logs in `.validation_logs/` |
| SkillForge AI tests pass | Yes | SkillForge pytest logs and summary JSON |
| 23 skills structurally pass | Yes | Agent skills structural eval output |
| Smoke MCP profile works | Yes | Smoke preflight/smoke summary JSON for `rail_12306` and `filesystem` |
| Full Toolathlon profile works | No (unless separately proven) | Full-profile validation logs |
| Production safe sandbox | No | Independent security review |
| Builds any tool | No | Unsupported/unbounded claim |
| Canonical release verified | Only with canonical pair | `verify_release_pair.sh` + matching evidence hash |

## Positioning Statement

This repository is a controlled local framework for generating, validating, packaging, and smoke-testing AI-agent tools and skills with evidence-bound release gates.

The release-gated Toolathlon smoke profile is limited to `rail_12306` and `filesystem`. Google Calendar remains optional/full-profile only and must not be claimed as part of the required smoke validation.

It must not be presented as production-safe, fully autonomous, or fully Toolathlon-validated unless those claims are separately proven.
