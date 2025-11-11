.PHONY: clean clean-test clean-pyc clean-build docs help
.DEFAULT_GOAL := help

help: Makefile
	  	@sed -n 's/^\([A-Za-z0-9_.-]*\):.*## \(.*\)$$/\t\1: \2/p' Makefile | sort | column -t -s ':'

build: clean ## Build the c libraries
	python setup.py build_ext --inplace

clean: clean-build clean-pyc clean-test ## remove all build, test, coverage and Python artifacts

clean-c: ## Clean compiled C code
	find . -name '*.so' -exec rm -f {} +

clean-build: ## Remove build artifacts
	rm -fr build/
	rm -fr dist/
	rm -fr .eggs/
	find . -name '*.egg-info' -exec rm -fr {} +
	find . -name '*.egg' -exec rm -f {} +

clean-pyc: ## Remove Python file artifacts
	find . -name '*.pyc' -exec rm -f {} +
	find . -name '*.pyo' -exec rm -f {} +
	find . -name '*~' -exec rm -f {} +
	find . -name '__pycache__' -exec rm -fr {} +

clean-test: ## Remove test and coverage artifacts
	rm -fr .tox/
	rm -f .coverage
	rm -fr htmlcov/
	rm -fr .pytest_cache

tests: ## Run the Python tests
	python setup.py test

coverage: ## Check Python code coverage
	coverage run --source pysnobal setup.py test
	coverage report -m
	coverage html
	$(BROWSER) htmlcov/index.html

docs: ## Generate Sphinx HTML documentation, including API docs
	rm -f docs/pysnobal.rst
	rm -f docs/modules.rst
	sphinx-apidoc -o docs/ pysnobal
	$(MAKE) -C docs clean
	$(MAKE) -C docs html

install: clean ## Install the Python package in editable mode
	python -m pip install -e .
