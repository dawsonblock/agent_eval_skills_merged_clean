.DEFAULT_GOAL := help

.PHONY: help
help:
	@echo "Available targets: test-no-cov, test"

.PHONY: test-no-cov
test-no-cov:
	PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 \
	python -m pytest \
		-p pytest_cov.plugin \
		-p pytest_jsonreport.plugin \
		-p pytest_timeout \
		-p pytest_asyncio.plugin \
		-o addopts= \
		--no-cov -q

.PHONY: test
test:
	PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 \
	python -m pytest \
		-p pytest_cov.plugin \
		-p pytest_jsonreport.plugin \
		-p pytest_timeout \
		-p pytest_asyncio.plugin \
		-q
