#!/usr/bin/make -f

install-dev-requirements:
	pip install -U pip
	pip install pipenv pre-commit

install-test-requirements:
	pipenv install --dev
	pipenv run python -c "import pipfile; pf = pipfile.load('Pipfile'); print('\n'.join(package+version if version != '*' else package for package, version in pf.data['default'].items()))" > requirements.txt

test-python:
	@echo "Running Python tests"
	pipenv run python run_tests.py || exit 1
	@echo ""

lint-python:
	@echo "Linting Python files"
	pipenv run flake8 --ignore=E501,E731,W503 --exclude=.git,compat.py --per-file-ignores='mocket/async_mocket.py:E999' mocket
	@echo ""

setup: develop
	pre-commit install

develop: install-dev-requirements install-test-requirements

test: lint-python test-python

safetest:
	export SKIP_TRUE_REDIS=1; export SKIP_TRUE_HTTP=1; make test

publish: install-test-requirements
	pipenv run python -m build --sdist .
	pipenv run twine upload --repository mocket dist/mocket-$(shell python -c 'import mocket; print(mocket.__version__)').tar.gz
	pipenv run anaconda upload dist/mocket-$(shell python -c 'import mocket; print(mocket.__version__)').tar.gz

clean:
	rm -rf *.egg-info dist/
	find . -type d -name __pycache__ -exec rm -rf {} \;

.PHONY: clean publish safetest test setup develop lint-python test-python install-test-requirements install-dev-requirements
