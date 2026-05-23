# Release Evidence Note — 2026-05-23

**Repository:** agent_eval_skills_merged_clean
**Branch:** main
**Commit:** a0b34ab7f88906ef4699a5edb43b4d8d5c1ff153
**Date:** 2026-05-23
**Classification:** Pruned smoke release candidate for controlled testing

---

## Archive Hashes

| Artifact | SHA256 |
|---|---|
| `agent_eval_skills_merged_clean-pruned-smoke.zip` | `8a94525e47c3c0bef54234435512ae4f8b8b53aa3eef3776115b2f4205d6d46e` |
| `agent_eval_skills_merged_clean-smoke-evidence-2026-05-23.zip` | `437c6048a12c69428b4c900b8dc5a2ce848422e30cb000180bdd6036f1e40830` |

---

## Validation Summary

| Check | Result |
|---|---|
| ToolForge (98 tests, 0 failures) | passed |
| Agent Skills (23 skills, 0 failures) | passed |
| Toolathlon smoke (3/3 targets) | passed |
| Docker smoke (3/3 targets, separate run) | passed |
| SKIP_EXISTING_ARTIFACTS gate | verified |

- `run_started_at`: 2026-05-23T20:47:11Z
- `run_finished_at`: 2026-05-23T20:47:54Z (43 s)
- `docker_checked_at`: 2026-05-23T20:49:14Z (separate run)
- `toolathlon_profile`: smoke
- `rc_smoke_gate_enforced`: true

---

## Evidence Commands

```bash
# Unified smoke validation
TOOLATHLON_PROFILE=smoke ENFORCE_RC_SMOKE_PROFILE=1 bash scripts/validate_smoke_workspace.sh

# Docker smoke validation (separate run)
cd toolathlon-gym-curated
TOOLATHLON_PROFILE=smoke bash scripts/validate_docker.sh
cd ..

# SKIP mode verification
SKIP_EXISTING_ARTIFACTS=1 bash scripts/validate_smoke_workspace.sh 2>&1 | grep -E 'skip|SKIP'

# Clean release archive
bash scripts/create_release_zip.sh --output ../agent_eval_skills_merged_clean-pruned-smoke.zip

# Evidence bundle
bash scripts/create_evidence_bundle.sh --date 20260523
```

---

## Manifest Reference

Machine-readable evidence manifest:
[`release_artifacts/RELEASE_EVIDENCE_MANIFEST_2026-05-23.json`](release_artifacts/RELEASE_EVIDENCE_MANIFEST_2026-05-23.json)

---

## Safety Statement

- Not production-grade. Not hostile-code-safe.
- Use disposable benchmark containers.
- Dependency and security audit required before broader deployment.
