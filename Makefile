PYTHON ?= python
RUNNER := scripts/run_tests.py

.PHONY: test test-allure test-allure-only

test:
	$(PYTHON) $(RUNNER)

test-allure:
	$(PYTHON) $(RUNNER) --allure

test-allure-only:
	$(PYTHON) $(RUNNER) --allure-only
