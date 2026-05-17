# ToolForge v0.1.0 (Prototype)

Initial tagged release of the ToolForge prototype.

## Highlights
- End-to-end generated-tool workflows validated in clean workspaces:
  - csv-cleaner
  - json-schema-validator
  - local-file-hasher
- Path safety enforcement verified for traversal attempts.
- Validation pipeline confirmed:
  - schema, security, MCP, skill, eval artifacts, tests, static safety checks
- Test/quality gates in repository context:
  - pytest: 79 passed
  - coverage: 63.33% (threshold 60%)
  - ruff: passed
  - mypy: passed
- Packaging checks verified required artifacts and excluded stale runtime/cache junk.
- macOS timeout parity established via GNU timeout (`gtimeout`).

## Notes
- This release is a prototype milestone and is not positioned as production-ready.
- Detailed evidence and command matrix are documented in:
  - docs/RELEASE_VERIFICATION_2026-05-17.md
