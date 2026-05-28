# Security Fixture Policy

This repository includes synthetic credential-like fixtures for tests and benchmark scenarios.

## Known Safe Fixture Types

- Synthetic `sk-*` values in benchmark or test data.
- Test PEM/private key material in fixture-only directories.
- Mock OAuth/API credential placeholders used for local simulation.

## Allowed Paths For Secret-Like Fixtures

- `tests/`
- `fixtures/`
- `examples/`
- benchmark task data directories

## Release Policy

- Real secrets outside allowed fixture paths fail release validation.
- Fixture secrets must be documented in this file.
- Toolathlon local MCP servers are benchmark fixtures and are not production-approved.
