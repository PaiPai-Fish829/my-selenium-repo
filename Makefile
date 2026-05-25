PYTHON ?= python
RUNNER := scripts/run_tests.py

.PHONY: test test-api test-demo test-allure test-allure-only

test:
	$(PYTHON) $(RUNNER)

test-api:
	$(PYTHON) $(RUNNER) tests/api

test-demo:
	$(PYTHON) -m pytest example/tests -v --test-env=demo

test-allure:
	$(PYTHON) $(RUNNER) --allure

test-allure-only:
	$(PYTHON) $(RUNNER) --allure-only
