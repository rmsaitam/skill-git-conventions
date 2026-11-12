PYTEST := pytest==9.2.0
PYTEST_COV := pytest-cov==7.1.0
BANDIT := bandit==1.9.4

.PHONY: setup test coverage validate security check

setup:
	uv venv
	uv pip install $(PYTEST) $(PYTEST_COV)

test:
	uv run --with $(PYTEST) --with $(PYTEST_COV) pytest -q

coverage:
	uv run --with $(PYTEST) --with $(PYTEST_COV) pytest --cov-branch --cov=scripts --cov=skills/commit/scripts --cov-report=term-missing --cov-fail-under=80

validate:
	python3 scripts/validate_plugin.py .

security:
	uvx $(BANDIT) -r skills/commit/scripts scripts -ll

check: coverage validate security
