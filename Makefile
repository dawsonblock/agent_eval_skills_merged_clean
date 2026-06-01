# ─────────────────────────────────────────────
#  Agent Eval & Skills Platform — root Makefile
#  All targets run from the repo root.
# ─────────────────────────────────────────────

.DEFAULT_GOAL := help
TOOLFORGE_DIR := ToolForge

# ── helpers ──────────────────────────────────

.PHONY: help
help:           ## Show this help
	@awk 'BEGIN{FS=":.*##"} /^[a-zA-Z_-]+:.*##/{printf "  \033[36m%-20s\033[0m %s\n",$$1,$$2}' $(MAKEFILE_LIST)

# ── development ──────────────────────────────

.PHONY: install
install:        ## Install ToolForge in editable mode with dev extras
	cd $(TOOLFORGE_DIR) && pip install -e ".[dev]" -q

.PHONY: test
test:           ## Run the full test suite
	cd $(TOOLFORGE_DIR) && \
	TOOLFORGE_TEST_USE_MODULE_CLI=1 \
	PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 \
	python -m pytest \
		-p pytest_cov.plugin \
		-p pytest_jsonreport.plugin \
		-p pytest_timeout \
		-p pytest_asyncio.plugin \
		-o addopts= \
		--timeout=300 \
		--cov=packages \
		--cov=apps \
		--cov-report=html \
		--cov-report=term-missing \
		--cov-fail-under=60 \
		-q

.PHONY: test-no-cov
test-no-cov:    ## Run tests without coverage
	cd $(TOOLFORGE_DIR) && \
	TOOLFORGE_TEST_USE_MODULE_CLI=1 \
	PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 \
	python -m pytest \
		-p pytest_jsonreport.plugin \
		-p pytest_timeout \
		-p pytest_asyncio.plugin \
		-o addopts= \
		--timeout=300 \
		-q
# CI recommendation: wrap with outer timeout, e.g., timeout 600 make test-no-cov

.PHONY: test-cov
test-cov:       ## Run tests with HTML coverage report
	cd $(TOOLFORGE_DIR) && \
	PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 \
	python -m pytest \
		-p pytest_cov.plugin \
		-p pytest_jsonreport.plugin \
		-p pytest_timeout \
		-p pytest_asyncio.plugin \
		-o addopts= \
		--timeout=300 \
		--cov=packages --cov=apps --cov-report=html -q
	@echo "Coverage report: $(TOOLFORGE_DIR)/htmlcov/index.html"

.PHONY: lint
lint:           ## Lint with ruff
	cd $(TOOLFORGE_DIR) && ruff check packages apps tests

.PHONY: fmt
fmt:            ## Auto-fix lint issues with ruff
	cd $(TOOLFORGE_DIR) && ruff check --fix packages apps tests

.PHONY: typecheck
typecheck:      ## Type-check with mypy
	cd $(TOOLFORGE_DIR) && mypy packages apps

.PHONY: check
check: lint typecheck test  ## lint + typecheck + test (full CI gate)

# ── demo: CSV proof path ─────────────────────

.PHONY: demo
demo:           ## Run the end-to-end CSV-cleaner proof path in a fresh tmp dir
	@bash scripts/demo_csv_cleaner.sh

.PHONY: demo-csv-tool
demo-csv-tool:  ## Alias for the CSV proof-path demo
	@bash scripts/demo_csv_cleaner.sh

# ── toolforge commands ───────────────────────

.PHONY: doctor
doctor:         ## Check ToolForge environment
	cd $(TOOLFORGE_DIR) && toolforge doctor

.PHONY: validate-csv
validate-csv:   ## Validate the csv-cleaner tool
	cd $(TOOLFORGE_DIR) && toolforge validate csv-cleaner

.PHONY: eval-csv
eval-csv:       ## Run evals for csv-cleaner (expects 100% pass rate)
	cd $(TOOLFORGE_DIR) && toolforge eval csv-cleaner

.PHONY: build-csv
build-csv:      ## Package csv-cleaner to dist/
	cd $(TOOLFORGE_DIR) && toolforge package csv-cleaner

.PHONY: release-zip
release-zip:    ## Build and validate a metadata-clean distribution ZIP
	bash scripts/create_release_zip.sh

.PHONY: package-clean-zip
package-clean-zip: ## Build requested pruned-smoke clean ZIP name/location
	bash scripts/package_clean_zip.sh

.PHONY: prepublish-gate
prepublish-gate: verify-release-pair ## Fail-closed local pre-publish gate for canonical attested pair

.PHONY: operator-release-gate-check
operator-release-gate-check: ## Run operator helper: verify canonical pair and print required check names
	bash scripts/operator_release_gate_check.sh

.PHONY: verify-release-gate-policy
verify-release-gate-policy: ## Verify release gate naming consistency across workflows/docs
	bash scripts/verify_release_gate_policy.sh

.PHONY: verify-release-policy-drift
verify-release-policy-drift: ## Verify canonical release-policy constants have not drifted across docs/manifests/logs
	bash scripts/validate_release_policy_drift.sh

.PHONY: verify-release-policy-drift-strict
verify-release-policy-drift-strict: ## Verify release-policy drift and require current .validation_logs agreement
	bash scripts/validate_release_policy_drift.sh --require-validation-logs

.PHONY: verify-release-classification-matrix
verify-release-classification-matrix: ## Verify classify_release_upload across canonical/new/wrapper/dirty/invalid cases
	bash scripts/verify_release_classification_matrix.sh

.PHONY: build-pruned-smoke-release
build-pruned-smoke-release: ## Rebuild canonical pruned-smoke release ZIP using repository packaging policy
	bash scripts/build_pruned_smoke_release.sh

.PHONY: prove-smoke-release
prove-smoke-release: ## Run end-to-end smoke release proof workflow
	bash scripts/prove_smoke_release.sh

.PHONY: prove-full-toolathlon-profile
prove-full-toolathlon-profile: ## Run optional full Toolathlon profile proof workflow
	bash scripts/prove_full_toolathlon_profile.sh

.PHONY: check-no-absolute-local-paths
check-no-absolute-local-paths: ## Fail if release-facing artifacts leak workstation absolute paths
	python scripts/check_no_absolute_local_paths.py

.PHONY: generate-release-manifest
generate-release-manifest: ## Generate machine-readable release manifest with file hashes
	python scripts/generate_release_manifest.py

.PHONY: verify-skillforge-baseline
verify-skillforge-baseline: ## Verify SkillForge baseline gates (structure, parity, candidate hash/hygiene, regression tests)
	bash scripts/verify_skillforge_baseline_gate.sh

.PHONY: skillforge-ai-summary-tests
skillforge-ai-summary-tests: ## Generate release_artifacts/skillforge_ai_test_summary.json
	bash scripts/generate_skillforge_ai_summaries.sh --tests-only

.PHONY: skillforge-ai-summary-e2e
skillforge-ai-summary-e2e: ## Generate release_artifacts/skillforge_ai_csv_cleaner_e2e_summary.json
	bash scripts/generate_skillforge_ai_summaries.sh --e2e-only

.PHONY: skillforge-ai-summary-validation
skillforge-ai-summary-validation: ## Generate release_artifacts/skillforge_ai_validation_summary.json
	bash scripts/generate_skillforge_ai_summaries.sh --validation-only

.PHONY: skillforge-ai-summaries
skillforge-ai-summaries: ## Generate all SkillForge AI summary artifacts
	bash scripts/generate_skillforge_ai_summaries.sh

.PHONY: build-skillforge-ai-candidate
build-skillforge-ai-candidate: ## Build clean SkillForge AI candidate ZIP and refresh candidate summary
	bash scripts/build_skillforge_ai_candidate_zip.sh

.PHONY: skillforge-evidence-bundle
skillforge-evidence-bundle: ## Build SkillForge-specific evidence bundle from release_artifacts summaries
	bash scripts/create_skillforge_evidence_bundle.sh

.PHONY: verify-skip-strictness
verify-skip-strictness: ## Verify strict SKIP_EXISTING_ARTIFACTS behavior for smoke MCP builds
	bash scripts/verify_skip_existing_artifacts_strict.sh

.PHONY: finalize-release-distribution
finalize-release-distribution: ## Run final canonical release/evidence distribution gate and emit publish note
	bash scripts/finalize_release_distribution.sh

.PHONY: publish-manifest
publish-manifest: ## Verify canonical pair and generate a concise publish manifest markdown file
	bash scripts/generate_publish_manifest.sh

.PHONY: classify-release-upload
classify-release-upload: ## Classify uploaded release ZIP as attested pair or unbound wrapper/source bundle
	@if [ -z "$(RELEASE_ZIP)" ]; then \
		echo "Usage: make classify-release-upload RELEASE_ZIP=/path/to/release.zip [EVIDENCE_ZIP=/path/to/evidence.zip] [JSON_OUTPUT=/path/to/verdict.json]"; \
		exit 1; \
	fi
	@args="--release $(RELEASE_ZIP)"; \
	if [ -n "$(EVIDENCE_ZIP)" ]; then args="$$args --evidence $(EVIDENCE_ZIP)"; fi; \
	if [ -n "$(JSON_OUTPUT)" ]; then args="$$args --json-output $(JSON_OUTPUT)"; fi; \
	bash scripts/classify_release_upload.sh $$args

.PHONY: operator-release-upload-triage
operator-release-upload-triage: ## Run upload triage helper and print manual check name
	@if [ -z "$(RELEASE_ZIP)" ]; then \
		echo "Usage: make operator-release-upload-triage RELEASE_ZIP=/path/to/release.zip [EVIDENCE_ZIP=/path/to/evidence.zip] [JSON_OUTPUT=/path/to/verdict.json]"; \
		exit 1; \
	fi
	@args="--release $(RELEASE_ZIP)"; \
	if [ -n "$(EVIDENCE_ZIP)" ]; then args="$$args --evidence $(EVIDENCE_ZIP)"; fi; \
	if [ -n "$(JSON_OUTPUT)" ]; then args="$$args --json-output $(JSON_OUTPUT)"; fi; \
	bash scripts/operator_release_upload_triage.sh $$args

# ── release gates ────────────────────────────

CANONICAL_RELEASE_ZIP := release_artifacts/agent_eval_skills_merged_clean-pruned-smoke.zip
CANONICAL_EVIDENCE_ZIP := release_artifacts/agent_eval_skills_merged_clean-smoke-evidence-2026-05-31.zip
UPLOAD_WRAPPER_ZIP ?= /tmp/agent_eval_skills_merged_clean-upload-wrapper.zip

.PHONY: clean-workspace-artifacts
clean-workspace-artifacts: ## Remove macOS metadata, cache dirs, and transient artifacts
	@bash scripts/clean_workspace_artifacts.sh

.PHONY: check-release-hash-consistency
check-release-hash-consistency: ## Verify release hash references are consistent
	@python3 scripts/check_release_hash_consistency.py

.PHONY: verify-release-pair
verify-release-pair: ## Verify release+evidence ZIPs match canonical attested filenames/hashes
	@python3 scripts/verify_release_pair.py

.PHONY: verify-evidence-bundle
verify-evidence-bundle: ## Verify evidence bundle satisfies smoke-profile policy
	@bash scripts/verify_evidence_bundle.sh --evidence $(CANONICAL_EVIDENCE_ZIP)

.PHONY: verify-source-bundle-hygiene
verify-source-bundle-hygiene: ## Verify canonical release ZIP satisfies source hygiene
	@bash scripts/verify_source_bundle_hygiene.sh --zip $(CANONICAL_RELEASE_ZIP)

.PHONY: verify-upload-wrapper-hygiene
verify-upload-wrapper-hygiene: ## Build upload wrapper ZIP and verify source hygiene
	@python3 scripts/build_upload_wrapper.py --out $(UPLOAD_WRAPPER_ZIP)
	@bash scripts/verify_source_bundle_hygiene.sh --zip $(UPLOAD_WRAPPER_ZIP)

.PHONY: validate-release-policy-drift
validate-release-policy-drift: ## Verify canonical release-policy constants have not drifted
	@bash scripts/validate_release_policy_drift.sh

.PHONY: verify-canonical-release-pair
verify-canonical-release-pair: ## Verify dist/release/ contains canonical pair with correct hashes
	@bash scripts/verify_canonical_release_pair.sh

.PHONY: secret-scan
secret-scan: ## Scan for real-looking secrets in the workspace
	@python3 scripts/check_for_real_secrets.py

.PHONY: absolute-path-scan
absolute-path-scan: ## Scan for absolute local path leaks in artifacts
	@python3 scripts/check_no_absolute_local_paths.py

.PHONY: test-root
test-root: ## Run root-level release-policy tests
	@cd tests && python3 -m pytest release_*.py -q 2>/dev/null || echo "No root release tests found (skipped)"

.PHONY: validate-agent-skill-packages
validate-agent-skill-packages: ## Validate all 23 agent skill package ZIPs
	@FAIL=0; COUNT=0; \
	for z in $$(find agent-skills-curated/packages -name '*.zip' -type f | sort); do \
		COUNT=$$((COUNT + 1)); \
		if ! python3 -c "import zipfile; zipfile.ZipFile('$$z').testzip()" 2>/dev/null; then \
			echo "FAIL: Invalid skill ZIP: $$z"; \
			FAIL=1; \
		fi; \
	done; \
	if [ "$$FAIL" -eq 1 ]; then exit 1; fi; \
	echo "PASS: $$COUNT skill packages validated"

.PHONY: toolathlon-smoke
toolathlon-smoke: ## Run Toolathlon smoke profile checks
	@bash scripts/check_toolathlon_smoke_profile.sh

.PHONY: classify-release
classify-release: ## Classify the canonical release pair from dist/release/
	@if [ -f dist/release/$(notdir $(CANONICAL_RELEASE_ZIP)) ]; then \
		bash scripts/classify_release_upload.sh \
			--release dist/release/$(notdir $(CANONICAL_RELEASE_ZIP)) \
			--evidence dist/release/$(notdir $(CANONICAL_EVIDENCE_ZIP)); \
	else \
		echo "dist/release/ not synced — run make sync-canonical-to-dist first"; \
		exit 1; \
	fi

.PHONY: final-release-gate
final-release-gate: clean-workspace-artifacts check-release-hash-consistency verify-release-pair verify-evidence-bundle verify-source-bundle-hygiene validate-release-policy-drift sync-canonical-to-dist verify-canonical-release-pair test-root validate-agent-skill-packages toolathlon-smoke secret-scan absolute-path-scan classify-release ## Run all release gates in sequence (syncs dist/release/ before checking)
	@echo ""
	@echo "== All release gates passed =="

.PHONY: sync-canonical-to-dist
sync-canonical-to-dist: ## Sync canonical release artifacts from release_artifacts/ to dist/release/ (verifies hashes)
	@python3 scripts/sync_canonical_to_dist.py

.PHONY: build-smoke-evidence
build-smoke-evidence: ## Build smoke evidence ZIP from validation logs
	@python3 scripts/build_evidence_zip.py --release-zip $(CANONICAL_RELEASE_ZIP)

.PHONY: update-release-lock
update-release-lock: ## Update release_lock.json with current release/evidence hashes
	@python3 scripts/build_pruned_smoke_release.py --update-lock

.PHONY: build-canonical-release
build-canonical-release: ## Full release build: clean → build release → build evidence → sync → final gate
	@echo "== Building Canonical Release =="
	@echo ""
	@$(MAKE) clean-workspace-artifacts
	@echo ""
	@$(MAKE) build-pruned-smoke-release
	@echo ""
	@$(MAKE) build-smoke-evidence
	@echo ""
	@$(MAKE) sync-canonical-to-dist
	@echo ""
	@$(MAKE) final-release-gate

.PHONY: rebuild-and-sync
rebuild-and-sync: ## Rebuild canonical release ZIP and sync to dist/release/
	@echo "== Rebuilding canonical release ZIP =="
	@python3 scripts/build_pruned_smoke_release.py --update-lock
	@echo ""
	@$(MAKE) sync-canonical-to-dist
	@echo ""
	@echo "Rebuild and sync complete."

.PHONY: update-doc-hashes
update-doc-hashes: ## Print commands to update documentation hashes to match current release_lock.json
	@echo "== Current hashes from release_lock.json =="
	@python3 -c "\
import json; \
lock = json.load(open('release_artifacts/release_lock.json')); \
print('Release SHA:', lock['release_sha256']); \
print('Evidence SHA:', lock['evidence_sha256']); \
print(); \
print('Update these files to match:'); \
print('  README.md'); \
print('  DEPLOYMENT.md'); \
print('  WORKSPACE_HEALTH_DASHBOARD.md'); \
print('  VALIDATION_EVIDENCE.md'); \
print('  RELEASE_NOTE_PUBLIC_*.md'); \
print('  scripts/canonical_release_attestation.env'); \
print('  RELEASE_STATUS.json'); \
print('  RELEASE_MANIFEST.json'); \
"

# ── clean ────────────────────────────────────

.PHONY: clean
clean:          ## Remove Python cache files and build artifacts (git-ignored anyway)
	find . -type d -name "__pycache__" -not -path "*/.git/*" -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -o -name "*.pyo" | xargs rm -f 2>/dev/null || true
	rm -rf $(TOOLFORGE_DIR)/htmlcov $(TOOLFORGE_DIR)/.coverage $(TOOLFORGE_DIR)/.pytest_cache $(TOOLFORGE_DIR)/.ruff_cache
	@echo "Clean done."
