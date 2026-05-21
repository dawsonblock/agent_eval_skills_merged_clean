# Validation Evidence

This document defines the minimum evidence required to claim release-candidate status for controlled testing.

## Required Artifacts

- `.validation_logs/validation_summary.json`
- `.validation_logs/toolathlon_preflight_summary.json`
- Phase logs in `.validation_logs/`

## Validation Commands

Run from repository root:

```bash
bash scripts/validate_workspace.sh
```

Run Docker proof when Docker is available:

```bash
cd toolathlon-gym-curated
docker build -t toolathlon:repair .
docker run --rm toolathlon:repair python scripts/preflight_mcp_paths.py --json-output /workspace/.validation_logs/toolathlon_preflight_summary.json
```

## Evidence Interpretation

`validation_summary.json` contains:

- `overall_status`
- `failed_phase_count`
- `capabilities` (Docker availability, Python support, requested modes)
- Per-phase status, duration, exit code, and log paths

`toolathlon_preflight_summary.json` contains:

- `found_count`
- `missing_count`
- `found` and `missing` path lists
- Timestamp and source directories

## Promotion Rule

Claim release-candidate status only when:

1. Required artifacts are present.
2. Required phases are `passed` in `validation_summary.json`.
3. Toolathlon preflight shows `missing_count = 0`.
4. Docker gate is proven in a Docker-capable environment or explicitly marked unavailable in the environment profile.

If any condition is not met, classify as strong repair candidate.
