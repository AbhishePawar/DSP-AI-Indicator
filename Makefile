.PHONY: install lint format test test-cov test-arch test-smoke test-integrity test-staging-safety ci-local clean

install:
	pip install -e ".[dev]"

lint:
	ruff check packages tests
	black --check packages tests

format:
	ruff check --fix packages tests
	black packages tests

test:
	pytest packages --import-mode=importlib -p no:cov

test-cov:
	pytest packages --import-mode=importlib --cov --cov-report=term-missing

test-arch:
	pytest packages -q --import-mode=importlib -p no:cov -k architecture --tb=short

test-smoke:
	pytest packages/dsp_platform/tests/test_asi_monorepo_smoke.py -q --import-mode=importlib -p no:cov --tb=short

test-integrity:
	python scripts/ci_repository_integrity.py


test-staging-safety:
	pytest \
		packages/production_platform/tests/test_staging_safety.py \
		packages/api_platform/tests/test_staging_safety_api.py \
		packages/production_platform/tests/test_product_state_backup.py \
		packages/api_platform/tests/test_p108_backup_restore.py \
		packages/api_platform/tests/test_health_rc1.py \
		packages/api_platform/tests/test_ops_api.py \
		-v --import-mode=importlib -p no:cov --tb=short

# Local parity with ASI-007 quality gates (excluding codecov upload).
ci-local: test-integrity test-arch test-smoke
	pytest packages -q --import-mode=importlib -p no:cov --tb=line
	ruff check packages tests
	black --check packages tests
	mypy

clean:
	rm -rf .pytest_cache .ruff_cache .coverage htmlcov dist build *.egg-info
	find . -type d -name __pycache__ -exec rm -rf {} +
