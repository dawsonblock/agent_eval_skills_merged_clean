# Release Gate Runbook

This runbook defines the exact GitHub settings flow to enforce attested-pair release governance.

## Goal

Only allow release-path changes and release publication when the canonical attested-pair checks pass.

## One-Command Operator Check

Use this command before configuring rules or preparing a release upload:

```bash
make operator-release-gate-check
```

This command:

1. Runs canonical attested-pair verification.
2. Prints the exact required check names to copy into branch protection or rulesets.

Final distribution gate command:

```bash
make finalize-release-distribution
```

This command enforces canonical hash matching, release ZIP hygiene, evidence bundle value checks, and emits the publish note text.

Publish manifest command:

```bash
make publish-manifest
```

This command fail-closes on the same final gate and writes `release_artifacts/PUBLISH_MANIFEST_CANONICAL_PAIR.md` for release body/handoff reuse.

If artifacts are stored outside the repository root:

```bash
bash scripts/operator_release_gate_check.sh \
   --release /path/to/agent_eval_skills_merged_clean-pruned-smoke.zip \
   --evidence /path/to/agent_eval_skills_merged_clean-smoke-evidence-2026-05-22.zip
```

Use this command to triage third-party uploaded wrappers before any release label claim:

```bash
make operator-release-upload-triage RELEASE_ZIP=/path/to/uploaded-wrapper.zip
```

Optional pair-aware triage when evidence is also provided:

```bash
make operator-release-upload-triage \
   RELEASE_ZIP=/path/to/uploaded-wrapper.zip \
   EVIDENCE_ZIP=/path/to/agent_eval_skills_merged_clean-smoke-evidence-2026-05-22.zip \
   JSON_OUTPUT=.validation_logs/release_upload_triage_verdict.json
```

## Required Checks

Configure these as required checks on the release path:

1. `Validate Workspace / Unified Workspace Validation`
2. `Validate Workspace / Verify Canonical Attested Pair`
3. `Validate Workspace / Classify Uploaded Release Artifact`

Manual pre-publish gate for distribution events:

1. `Release Attested Pair Gate / Verify Canonical Attested Pair`

Manual upload triage record for wrapper/source uploads:

1. `Release Upload Triage / Classify Uploaded Release Artifact`

## Option A: Branch Protection (main)

Use this when your repository uses branch protection rules directly.

1. Open repository `Settings`.
2. Select `Branches`.
3. Under `Branch protection rules`, create or edit the rule for `main`.
4. Enable `Require a pull request before merging`.
5. Enable `Require approvals` and set required reviewer count.
6. Enable `Require status checks to pass before merging`.
7. In required checks, add:
   - `Validate Workspace / Unified Workspace Validation`
   - `Validate Workspace / Verify Canonical Attested Pair`
   - `Validate Workspace / Classify Uploaded Release Artifact`
8. Enable `Require branches to be up to date before merging`.
9. Save the rule.

## Option B: Repository Ruleset (recommended for org-scale governance)

Use this when you manage protections through rulesets.

1. Open repository `Settings`.
2. Select `Rules` then `Rulesets`.
3. Create ruleset and target branch pattern `main` (or your release branch pattern).
4. Add rule: `Require a pull request before merging`.
5. Add rule: `Require approvals`.
6. Add rule: `Require status checks to pass`.
7. Add required checks:
   - `Validate Workspace / Unified Workspace Validation`
   - `Validate Workspace / Verify Canonical Attested Pair`
   - `Validate Workspace / Classify Uploaded Release Artifact`
8. Save and enable the ruleset.

## Manual Pre-Publish Procedure

Before any release upload/distribution event:

1. Run workflow `Release Attested Pair Gate`.
2. Confirm policy consistency step passes (`verify_release_gate_policy.sh`).
3. Confirm strict skip regression check passes (`make verify-skip-strictness`).
4. Confirm job `Verify Canonical Attested Pair` passes.
5. Publish only the verified pair from that run.

If this workflow fails, classify the candidate as an unbound wrapper/source bundle and do not publish as release-candidate.

## Manual Upload Triage Procedure

Before acting on externally uploaded ZIP files:

1. Run local operator triage command:
   - `make operator-release-upload-triage RELEASE_ZIP=/path/to/uploaded-wrapper.zip`
2. Optionally add evidence path when testing an exact pair:
   - `make operator-release-upload-triage RELEASE_ZIP=/path/to/uploaded-wrapper.zip EVIDENCE_ZIP=/path/to/agent_eval_skills_merged_clean-smoke-evidence-2026-05-22.zip JSON_OUTPUT=.validation_logs/release_upload_triage_verdict.json`
3. Confirm classification output completes.
4. Treat any non-canonical result as unbound wrapper/source bundle.
5. Preserve the JSON verdict artifact for audit records.

## Release-Path Checklist

1. Required checks are configured and active.
2. PR merge checks pass on the release branch.
3. Manual pre-publish gate run is green for the exact files to be published.
4. Published artifacts match attested filenames and hashes.

## Recovery Path When Hashes Change

If bytes differ from canonical attestation:

1. Do not publish under existing release label.
2. Regenerate evidence for the new artifact pair.
3. Issue a new manifest and attestation.
4. Publish only after the new pair is verified and approved.
