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

# ── clean ────────────────────────────────────

.PHONY: clean
clean:          ## Remove Python cache files and build artifacts (git-ignored anyway)
	find . -type d -name "__pycache__" -not -path "*/.git/*" -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -o -name "*.pyo" | xargs rm -f 2>/dev/null || true
	rm -rf $(TOOLFORGE_DIR)/htmlcov $(TOOLFORGE_DIR)/.coverage $(TOOLFORGE_DIR)/.pytest_cache $(TOOLFORGE_DIR)/.ruff_cache
	@echo "Clean done."
