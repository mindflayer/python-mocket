develop:
	pip install -q "file://`pwd`/#egg=python-mocket[dev]"
	pip install -q "file://`pwd`/#egg=python-mocket[tests]"
	pip install -q -e . --use-mirrors

install-test-requirements:
	pip install -q "file://`pwd`/#egg=python-mocket[tests]"

test: install-test-requirements lint-python test-python

test-python:
	@echo "Running Python tests"
	python setup.py -q test || exit 1
	@echo ""

lint-python:
	@echo "Linting Python files"
	flake8 --exit-zero --ignore=E501 mocket
	@echo ""
