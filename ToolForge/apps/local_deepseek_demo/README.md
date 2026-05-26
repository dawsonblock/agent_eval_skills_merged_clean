# Local DeepSeek Tool UI Demo

This demo provides a local web UI for chatting with DeepSeek and running ToolForge tools with approval and validation checks.

## What it includes

- FastAPI backend with chat, tool list, planning, creation, validation, and run endpoints.
- Local static UI for settings, chat, registry preview, execution logs, and output viewer.
- Local-safe guardrails for tool execution:
  - blocked path traversal and sensitive locations
  - restricted permissions for `read_secrets` and `shell_commands`
  - explicit approval required before execution
  - generated tools written under `ToolForge/generated_tools`

## Environment

Set values in the repository root `.env` file (copy from `.env.example`):

- `DEEPSEEK_API_KEY`
- `DEEPSEEK_BASE_URL` (default: `https://api.deepseek.com`)
- `DEEPSEEK_MODEL` (default: `deepseek-chat`)
- `TOOLFORGE_DEMO_HOST` (default: `127.0.0.1`)
- `TOOLFORGE_DEMO_PORT` (default: `8787`)
- `TOOLFORGE_SANDBOX_MODE` (default: `local_safe`)

## Launch

From repository root:

```bash
scripts/run_deepseek_tool_ui.sh
```

Options are forwarded to the ToolForge launcher:

```bash
scripts/run_deepseek_tool_ui.sh --lan
scripts/run_deepseek_tool_ui.sh --host 127.0.0.1 --port 8787
scripts/run_deepseek_tool_ui.sh --no-reload
```

## API endpoints

- `GET /`
- `GET /api/health`
- `GET /api/models`
- `GET /api/tools`
- `POST /api/chat`
- `POST /api/tools/run`
- `POST /api/tools/plan`
- `POST /api/tools/create`
- `POST /api/tools/validate`
- `GET /api/output`
- `GET /api/open-output-folder`

## Known gaps

- The demo is intended for local development and validation, not production multi-user hosting.
- CORS defaults are localhost-oriented and can be extended via `TOOLFORGE_DEMO_CORS_ORIGINS`.
- Generated tools should be reviewed before wider use.
