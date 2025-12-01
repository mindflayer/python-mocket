#!/usr/bin/make -f

VENV_PATH = .venv/bin

install-dev-requirements:
	curl -LsSf https://astral.sh/uv/install.sh | sh
	uv venv && uv pip install hatch

install-test-requirements:
	uv pip install --editable .[test]

prepare-hosts: _services-up
	@bash scripts/patch_hosts.sh

_services-up:
	docker compose up -d

services-up: _services-up prepare-hosts

services-down:
	docker compose down --remove-orphans

setup: develop
	pre-commit install

develop: install-dev-requirements install-test-requirements

types:
	@if [ -n "$$SKIP_MYPY" ]; then \
		echo "Skipping mypy types check because SKIP_MYPY is set"; \
	else \
		echo "Type checking Python files"; \
		$(VENV_PATH)/mypy --pretty; \
	fi
	@echo ""

test: types
	@echo "Running Python tests"
	uv pip uninstall pook || true
	$(VENV_PATH)/wait-for-it --service httpbin.local:443 --service localhost:6379 --timeout 5 -- $(VENV_PATH)/pytest
	uv pip install pook && $(VENV_PATH)/pytest tests/test_pook.py && uv pip uninstall pook
	@echo ""

safetest:
	SKIP_TRUE_REDIS=1 SKIP_TRUE_HTTP=1 $(VENV_PATH)/pytest

publish: clean install-test-requirements
	uv build --package mocket --sdist --wheel
	uv publish

clean:
	rm -rf *.egg-info dist/ requirements.txt uv.lock coverage.xml || true
	find . -type d -name __pycache__ -exec rm -rf {} \; || true

.PHONY: clean publish safetest test setup develop lint-python test-python _services-up
.PHONY: prepare-hosts services-up services-down install-test-requirements install-dev-requirements
