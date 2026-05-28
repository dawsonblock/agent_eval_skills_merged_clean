# Toolathlon Validation Profiles

This repository supports two validation profiles.

## smoke

- servers:
  - rail_12306
  - filesystem
- status: supported
- purpose: release validation
- build command: `./scripts/build_smoke_artifacts.sh`
- run command: `./scripts/run_smoke_profile.sh`

## full

- servers: all local MCP servers in `profiles/full/mcp_servers.json`
- status: experimental / incomplete
- purpose: development diagnostics only
- run command: `python scripts/smoke_mcp_servers.py --profile full`

The smoke profile is the only release-gated path. Full profile failures do not
represent release regressions unless explicitly run with `--strict`.# Toolathlon Profiles

## smoke

Release-gated profile.

Targets:
- rail_12306
- filesystem

Claims allowed:
- local import/start smoke validation
- profile-aware MCP target availability for smoke targets

Claims not allowed:
- full benchmark validity
- production integration safety

## full

Experimental, non-release-gated profile.

Targets:
- rail_12306
- filesystem
- google_calendar
- canvas
- howtocook
- memory
- google_forms
- fetch
- notion
- woocommerce
- youtube
- youtube_transcript

Google Calendar remains optional/full-profile only and is not part of the
release-gated smoke profile.

Claims allowed only when full-profile validation logs are present and linked to the exact artifact pair being claimed.
