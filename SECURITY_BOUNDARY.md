# Security Boundary

This document defines the security protections, limitations, and sandbox model for the agent_eval_skills_merged_clean workspace.

## What Is Protected

- **Path traversal prevention**: Tool specs attempting `../../../` access are rejected by the schema validator.
- **Secret environment stripping**: Sandbox execution removes environment variables matching `*KEY*`, `*TOKEN*`, `*SECRET*`, `*PASSWORD*`, `OPENAI_*`, `ANTHROPIC_*`, `DEEPSEEK_*`, `GITHUB_*`.
- **Absolute path leak detection**: Release artifacts are scanned for embedded workstation paths (`/Users/...`, `/home/...`).
- **Real secret scanning**: Automated scan for API keys, tokens, and credentials before release.
- **Source bundle hygiene**: Release ZIPs are validated for forbidden entries (`node_modules`, `__pycache__`, `.DS_Store`, `__MACOSX`, `.validation_logs`).

## What Is NOT Protected

- **Hostile-code execution safety**: This workspace is NOT hardened against arbitrary untrusted code. Do not run untrusted Toolathlon servers on your host directly.
- **Production security audit**: This workspace has NOT undergone a formal production security review.
- **Full Toolathlon isolation**: Only 2 MCP servers are smoke-validated; the remaining 23 MCP configs are not release-validated.
- **Network containment**: Docker no-network mode exists conceptually but requires Docker to be operational.
- **npm dependency vulnerabilities**: Third-party MCP servers have known npm vulnerabilities documented in `docs/npm-vulnerability-report.md`.

## Sandbox Levels

| Level | Name | Network | Shell | Filesystem |
|-------|------|---------|-------|------------|
| 0 | None | Unrestricted | Unrestricted | Unrestricted |
| 1 | Basic | Unrestricted | Unrestricted | Workspace-only |
| 2 | Restricted | Denied | Denied | Workspace-only |
| 3 | Docker | Denied | Denied | Container-only |
| 4 | Docker + No-Network | Denied | Denied | Container-only |

Default: Level 2 (Restricted).

## Docker Protection

- **What Docker protects**: Process isolation, filesystem containment, network namespace control.
- **What Docker does NOT protect**: Supply chain attacks via legitimate dependencies, resource exhaustion, side-channel attacks.
- **Requirement**: Docker must be installed and running for sandbox levels 3 and 4.

## How to Run Untrusted Code Safely

1. Use sandbox level >= 3 (Docker).
2. Verify `sandbox_profile.json` default-deny settings are active.
3. Ensure no real credentials are present in the execution environment.
4. Monitor execution logs for unexpected network or filesystem access.
5. Use disposable containers — do not reuse container instances between untrusted runs.

## How to Report Vulnerabilities

Open an issue with the label `security` or contact the workspace maintainers directly. Do not open public issues for active security vulnerabilities.
