#!/usr/bin/make -f

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
	@echo "Type checking Python files"
	.venv/bin/mypy --pretty
	@echo ""

test: types
	@echo "Running Python tests"
	export VIRTUAL_ENV=.venv; .venv/bin/wait-for-it --service httpbin.local:443 --service localhost:6379 --timeout 5 -- .venv/bin/pytest
	@echo ""

safetest:
	export SKIP_TRUE_REDIS=1; export SKIP_TRUE_HTTP=1; make test

publish: clean install-test-requirements
	uv run python3 -m build --sdist .
	uv run twine upload --repository mocket dist/*.tar.gz

clean:
	rm -rf *.egg-info dist/ requirements.txt uv.lock || true
	find . -type d -name __pycache__ -exec rm -rf {} \; || true

.PHONY: clean publish safetest test setup develop lint-python test-python _services-up
.PHONY: prepare-hosts services-up services-down install-test-requirements install-dev-requirements
