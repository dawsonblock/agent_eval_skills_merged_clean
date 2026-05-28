# Clean Checkout Validation

This runbook reproduces smoke release validation from a clean checkout and records canonical artifact identity.

## Prerequisites

- Python 3.12 available as `python3`
- Node.js 20+ available as `node`
- `npm` available

## Procedure

1. Clone and enter workspace.

```bash
git clone <repo-url>
cd agent_eval_skills_merged_clean
```

1. Install Python dependencies.

```bash
python3 -m pip install --upgrade pip
python3 -m pip install -e "ToolForge[dev]"
```

1. Install Toolathlon smoke dependencies.

```bash
bash scripts/install_toolathlon_smoke_deps.sh
```

1. Build deterministic pruned smoke release ZIP.

```bash
python3 scripts/build_pruned_smoke_release.py --profile smoke
```

1. Collect smoke evidence and build evidence ZIP.

```bash
bash scripts/collect_smoke_evidence.sh
```

1. Sync lock-backed metadata and compute identity.

```bash
python3 scripts/write_release_metadata.py
python3 scripts/compute_release_identity.py
```

1. Run final gate checks.

```bash
python3 scripts/sync_release_metadata_from_lock.py
python3 scripts/sanitize_release_paths.py
python3 scripts/check_release_hash_consistency.py
python3 scripts/verify_release_pair.py \
  --release release_artifacts/agent_eval_skills_merged_clean-pruned-smoke.zip \
  --evidence "$(ls -1t release_artifacts/agent_eval_skills_merged_clean-smoke-evidence-*.zip | head -n1)" \
  --strict
pytest -q tests
bash scripts/verify_source_bundle_hygiene.sh \
  --zip release_artifacts/agent_eval_skills_merged_clean-pruned-smoke.zip
python3 scripts/check_no_absolute_local_paths.py --strict
python3 scripts/check_for_real_secrets.py
bash scripts/check_toolathlon_smoke_profile.sh
```

## Expected Outputs

- `release_artifacts/release_lock.json`
- `release_artifacts/release_identity.generated.json`
- `RELEASE_STATUS.json` and `RELEASE_MANIFEST.json` synced from lock
- Latest evidence ZIP under `release_artifacts/agent_eval_skills_merged_clean-smoke-evidence-<date>.zip`
- All gate commands return zero exit status
