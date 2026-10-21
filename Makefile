.PHONY: clean clean-test clean-pyc clean-build help
.DEFAULT_GOAL := help

help: Makefile
	@sed -n 's/^\([A-Za-z0-9_.-]*\):.*## \(.*\)$$/\1:\2/p' $(MAKEFILE_LIST) | sort | column -t -s ':'

build: clean ## Build the compiled libraries
	python setup.py build_ext --inplace

clean: clean-build clean-pyc clean-test ## remove all build, test, and Python artifacts

clean-build: ## Remove build artifacts
	# Cython build artifacts
	find . -type f -name '*.so' -delete
	rm -fr build/
	# Python packaging artifacts
	rm -fr dist/
	rm -fr .eggs/
	find . -name '*.egg-info' -exec rm -fr {} +
	find . -name '*.egg' -exec rm -f {} +

clean-pyc: ## Remove Python file artifacts
	find . -name '*.pyc' -exec rm -f {} +
	find . -name '*.pyo' -exec rm -f {} +
	find . -name '*~' -exec rm -f {} +
	find . -name '__pycache__' -exec rm -fr {} +

clean-test: ## Remove testartifacts
	rm -fr .pytest_cache

tests: install-dev ## Run the Python tests
	pytest

install: clean ## Install the package with runtime dependencies
	python -m pip install -e .

install-dev: build ## Install the package with development dependencies but no runtime dependencies
	python -m pip install --group dev
	python -m pip install --no-deps -e .
