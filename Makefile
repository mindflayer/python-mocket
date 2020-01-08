#!/usr/bin/make -f

install-dev-requirements:
	pip install -U -q -e .

install-test-requirements:
	pip install -U pip
	pip install -U -q -e .[tests]

test-python:
	@echo "Running Python tests"
	python setup.py -q test || exit 1
	@echo ""

lint-python:
	@echo "Linting Python files"
	flake8 --ignore=E501,E731 --exclude=.git,compat.py mocket
	@echo ""

develop: install-test-requirements install-dev-requirements
	mkdir -p shippable/testresults
	mkdir -p shippable/codecoverage

test: install-test-requirements lint-python test-python

test-ci: install-test-requirements lint-python
	python runtests.py --junitxml=shippable/testresults/nosetests.xml \
	--cov-report=xml:shippable/codecoverage/coverage.xml

safetest:
	export SKIP_TRUE_REDIS=1; export SKIP_TRUE_HTTP=1; make test

publish:
	python setup.py sdist
	pip install -U twine
	twine upload dist/mocket-$(shell python -c 'import mocket; print(mocket.__version__)')*.*
	pip install -U anaconda-client
	anaconda upload dist/mocket-$(shell python -c 'import mocket; print(mocket.__version__)').tar.gz

clean:
	rm -rf dist shippable
	rm -rf *.egg-info
	find . -type d -name __pycache__ -exec rm -rf {} \;

.PHONY: clean publish safetest test test-ci develop lint-python test-python install-test-requirements install-dev-requirements

