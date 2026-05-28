# Security Fixture Policy

This repository contains benchmark and test fixtures that may resemble secrets.

Allowed fixture locations:
- tests/
- fixtures/
- examples/
- toolathlon-gym-curated task data
- Playwright test assets

Rules:
- Real credentials are not allowed.
- Synthetic keys must be documented as fixtures.
- Real-looking secrets outside allowed fixture paths fail release validation.
- Toolathlon MCP servers are benchmark fixtures and are not production services.
