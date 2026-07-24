.PHONY: install lint format test test-cov clean

install:
	pip install -e ".[dev]"

lint:
	ruff check packages tests
	black --check packages tests

format:
	ruff check --fix packages tests
	black packages tests

test:
	pytest

test-cov:
	pytest --cov=core --cov=dsp --cov-report=term-missing

clean:
	rm -rf .pytest_cache .ruff_cache .coverage htmlcov dist build *.egg-info
	find . -type d -name __pycache__ -exec rm -rf {} +
