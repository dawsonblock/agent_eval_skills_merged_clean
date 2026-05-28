# Repair Plan 2026-05-27

## Objective

Stabilize release identity so canonical release/evidence artifacts are reproducible, hash-bound, and CI-verified from a clean checkout.

## Delivered in this phase

- Added `scripts/compute_release_identity.py` for lock-aware canonical identity output.
- Added `scripts/write_release_metadata.py` to orchestrate lock write, metadata sync, manifest regeneration, and identity output.
- Added `scripts/install_toolathlon_smoke_deps.sh` for deterministic smoke dependency bootstrap.
- Added `scripts/collect_smoke_evidence.sh` for smoke evidence collection and ZIP generation.
- Added clean-checkout runbook at `docs/CLEAN_CHECKOUT_VALIDATION.md`.

## Remaining follow-up

- Keep all workflows pinned to the active lock evidence date/hash.
- Maintain lock-first policy: edit lock, then sync derived files.
- Run clean-checkout runbook before release promotion.
