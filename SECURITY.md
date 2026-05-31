# Security Scope

This repository is validated as a local benchmark and evaluation workspace.

## Status

- Security status: controlled local benchmark only.
- Production deployment: not approved.

# Security Status
This repository is not approved for production deployment.
The Toolathlon local MCP servers are local benchmark fixtures. They may contain dependency warnings and should run only in isolated local development environments.
The smoke release validates reproducibility and launch behavior. It does not certify runtime security for public or production exposure.

## Constraints

- Toolathlon local MCP servers are fixture workloads intended for isolated local testing.
- npm audit findings in fixture servers are treated as benchmark risk signals and warn-only for smoke validation.
- Production security hardening, hostile-code isolation, and dependency remediation are outside the smoke release claim.

## Known npm Vulnerabilities (Smoke MCP Servers)

As of 2026-05-31, the two smoke-gated MCP servers have known npm vulnerabilities:

### 12306-mcp (14 vulnerabilities: 7 high, 6 moderate, 1 low)

| Package | Severity | Issues | Fix |
|---------|----------|--------|-----|
| axios | high | SSRF, DoS, prototype pollution | >=1.16.0 |
| @modelcontextprotocol/sdk | high | ReDoS, data leak, DNS rebinding | >=1.25.2 |
| @modelcontextprotocol/inspector | high | XSS command execution | >=0.16.6 |
| lodash | high | Code injection via _.template | >=4.17.24 |
| minimatch | high | ReDoS via wildcards | >=3.1.4 |
| path-to-regexp | high | DoS, ReDoS | >=8.4.0 |

See: `toolathlon-gym-curated/local_servers/12306-mcp/NPM_AUDIT.json`

### filesystem / @modelcontextprotocol/server-filesystem (15 vulnerabilities: 2 high, 13 moderate)

| Package | Severity | Issues | Fix |
|---------|----------|--------|-----|
| fast-uri | high | Path traversal, host confusion | >=3.1.2 |
| path-to-regexp | high | DoS, ReDoS | >=8.4.0 |
| hono | moderate | Prototype pollution, path traversal, middleware bypass | >=4.12.18 |
| @hono/node-server | moderate | Middleware bypass | >=1.19.13 |

See: `toolathlon-gym-curated/local_servers/filesystem/NPM_AUDIT.json`

Versions have been pinned to patched ranges in both `package.json` files. Full remediation requires `npm install` in each server directory. These servers should only run in disposable containers for benchmark purposes.

For detailed vulnerability reports, see `docs/npm-vulnerability-report.md`.

## Requirements for Production Consideration

1. Complete dependency security review and remediation.
2. Runtime isolation/hardening assessment.
3. Secret and credential handling audit.
4. Explicit approval via a separate production security attestation.
