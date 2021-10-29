.PHONY: clean clean-test clean-pyc clean-build docs help
.DEFAULT_GOAL := help

define BROWSER_PYSCRIPT
import os, webbrowser, sys

from urllib.request import pathname2url

webbrowser.open("file://" + pathname2url(os.path.abspath(sys.argv[1])))
endef
export BROWSER_PYSCRIPT

define PRINT_HELP_PYSCRIPT
import re, sys

for line in sys.stdin:
	match = re.match(r'^([a-zA-Z_-]+):.*?## (.*)$$', line)
	if match:
		target, help = match.groups()
		print("%-20s %s" % (target, help))
endef
export PRINT_HELP_PYSCRIPT

BROWSER := python -c "$$BROWSER_PYSCRIPT"

ifndef PYTHON_VERSION
PYTHON_VERSION	:= python38
endif

help:
	@python -c "$$PRINT_HELP_PYSCRIPT" < $(MAKEFILE_LIST)

clean: clean-build clean-pyc clean-test ## remove all build, test, coverage and Python artifacts

clean-build: ## remove build artifacts
	rm -fr build/
	rm -fr dist/
	rm -fr .eggs/
	find . -name '*.egg-info' -exec rm -fr {} +
	find . -name '*.egg' -exec rm -rf {} +

clean-pyc: ## remove Python file artifacts
	find . -name '*.pyc' -exec rm -f {} +
	find . -name '*.pyo' -exec rm -f {} +
	find . -name '*~' -exec rm -f {} +
	find . -name '__pycache__' -exec rm -fr {} +

clean-test: ## remove test and coverage artifacts
	rm -fr .tox/
	rm -f .coverage
	rm -fr htmlcov/
	rm -fr .pytest_cache

lint: ## check style with flake8
	flake8 cfn_kafka_admin tests

test: ## run tests quickly with the default Python
	pytest -svx tests/

test-all: ## run tests on every Python version with tox
	tox

coverage: ## check code coverage quickly with the default Python
	coverage run --source cfn_kafka_admin -m pytest
	coverage report -m
	coverage html
	$(BROWSER) htmlcov/index.html

docs: ## generate Sphinx HTML documentation, including API docs
	rm -f docs/cfn_kafka_admin.rst
	rm -f docs/modules.rst
	sphinx-apidoc -o docs/ cfn_kafka_admin
	$(MAKE) -C docs clean
	$(MAKE) -C docs html
	$(BROWSER) docs/_build/html/index.html

servedocs: docs ## compile the docs watching for changes
	watchmedo shell-command -p '*.rst' -c '$(MAKE) -C docs html' -R -D .

conform	: ## Conform to a standard of coding syntax
	isort --profile black cfn_kafka_admin
	black cfn_kafka_admin tests
	find cfn_kafka_admin -name "*.json" -type f  -exec sed -i '1s/^\xEF\xBB\xBF//' {} +


python39	: clean
			test -d layer && rm -rf layer || mkdir layer
			docker run -u $(shell bash -c 'id -u'):$(shell bash -c 'id -u') \
			--rm -v $(PWD):/opt --entrypoint /bin/bash \
			public.ecr.aws/compose-x/python:3.9 \
			-c "ls -lA dist; pip install --no-cache-dir /opt/dist/*.whl -t /opt/layer"

python38	: clean
			test -d layer && rm -rf layer || mkdir layer
			docker run -u $(shell bash -c 'id -u'):$(shell bash -c 'id -u') \
			--rm -v $(PWD):/opt --entrypoint /bin/bash \
			public.ecr.aws/compose-x/python:3.8 \
			-c "ls -lA dist; pip install --no-cache-dir /opt/dist/*.whl -t /opt/layer"

python37	: clean
			test -d layer && rm -rf layer || mkdir layer
			docker run -u $(shell bash -c 'id -u'):$(shell bash -c 'id -u') \
			--rm -v $(PWD):/opt --entrypoint /bin/bash \
			public.ecr.aws/compose-x/python:3.7 \
			-c "ls dist ; pip install --no-cache-dir /opt/dist/*.whl -t /opt/layer"


dist:		clean ## builds source and wheel package
			poetry build

package:	dist $(PYTHON_VERSION)
			cleanpy -af --include-testing layer/

data-model:
		datamodel-codegen --input cfn_kafka_admin/specs/aws-cfn-kafka-admin-provider-schema.json \
		--input-file-type jsonschema \
		--output cfn_kafka_admin/models/admin.py --reuse-model
#		--enum-field-as-literal all


release: dist ## package and upload a release
	twine check dist/*
	poetry publish --build

release-test: dist ## package and upload a release
	twine check dist/* || echo Failed to validate release
	poetry config repositories.pypitest https://test.pypi.org/legacy/
	poetry publish -r pypitest --build

dist: clean ## builds source and wheel package
	poetry build
	ls -l dist

install: clean data-model conform ## install the package to the active Python's site-packages
	pip install . --use-pep517 #--use-feature=in-tree-build
