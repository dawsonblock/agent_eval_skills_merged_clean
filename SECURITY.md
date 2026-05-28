# Security Scope

This repository is validated as a local benchmark and evaluation workspace.

## Status

- Security status: controlled local benchmark only.
- Production deployment: not approved.

## Constraints

- Toolathlon local MCP servers are fixture workloads intended for isolated local testing.
- npm audit findings in fixture servers are treated as benchmark risk signals and warn-only for smoke validation.
- Production security hardening, hostile-code isolation, and dependency remediation are outside the smoke release claim.

## Requirements for Production Consideration

1. Complete dependency security review and remediation.
2. Runtime isolation/hardening assessment.
3. Secret and credential handling audit.
4. Explicit approval via a separate production security attestation.
