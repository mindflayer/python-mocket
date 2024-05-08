#!/usr/bin/make -f

install-dev-requirements:
	curl -LsSf https://astral.sh/uv/install.sh | sh
	uv venv && uv pip install hatch

install-test-requirements:
	uv pip install --editable .[test]

services-up:
	docker compose up -d

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
	export VIRTUAL_ENV=.venv; .venv/bin/wait-for-it --service httpbin.local:443 --service localhost:6379 --timeout 5 -- .venv/bin/pytest tests/ || exit 1
	@echo ""

safetest:
	export SKIP_TRUE_REDIS=1; export SKIP_TRUE_HTTP=1; make test

publish: install-test-requirements
	python -m build --sdist .
	twine upload --repository mocket dist/mocket-$(shell python -c 'import mocket; print(mocket.__version__)').tar.gz

clean:
	rm -rf *.egg-info dist/ requirements.txt Pipfile.lock
	find . -type d -name __pycache__ -exec rm -rf {} \;

.PHONY: clean publish safetest test setup develop lint-python test-python
.PHONY: services-up services-down install-test-requirements install-dev-requirements
