#!/usr/bin/make -f

install-dev-requirements:
	pip install -U -q -e .

install-test-requirements:
	pip install -U -q -e .[tests]

test-python:
	@echo "Running Python tests"
	python setup.py -q test || exit 1
	@echo ""

lint-python:
	@echo "Linting Python files"
	flake8 --exit-zero --ignore=E501 --exclude=.git,compat.py mocket
	@echo ""

develop: install-test-requirements install-dev-requirements

test: install-test-requirements lint-python test-python

safetest:
	export SKIP_TRUE_REDIS=1; export SKIP_TRUE_HTTP=1; make test

publish:
	python setup.py sdist upload
	pip install anaconda-client
	anaconda upload dist/mocket-$(shell python -c 'import mocket; print(mocket.__version__)').tar.gz

clean:
	rm -rf dist
	rm -rf *.egg-info
	find . -type d -name __pycache__ -exec rm -rf {} \;

.PHONY: publish clean

