#!/usr/bin/make -f

install-dev-requirements:
	pipenv install --dev -e .

install-test-requirements:
	pip install -U pip pipenv
	pipenv install --dev

test-python:
	@echo "Running Python tests"
	python setup.py -q test || exit 1
	@echo ""

lint-python:
	@echo "Linting Python files"
	flake8 --ignore=E501,E731,W503 --exclude=.git,compat.py mocket
	@echo ""

develop: install-test-requirements install-dev-requirements

test: install-test-requirements lint-python test-python

safetest:
	export SKIP_TRUE_REDIS=1; export SKIP_TRUE_HTTP=1; make test

publish:
	python setup.py sdist
	pipenv install --dev twine
	twine upload dist/mocket-$(shell python -c 'import mocket; print(mocket.__version__)')*.*
	pipenv install --dev anaconda-client
	anaconda upload dist/mocket-$(shell python -c 'import mocket; print(mocket.__version__)').tar.gz

clean:
	rm -rf *.egg-info
	find . -type d -name __pycache__ -exec rm -rf {} \;

.PHONY: clean publish safetest test develop lint-python test-python install-test-requirements install-dev-requirements
