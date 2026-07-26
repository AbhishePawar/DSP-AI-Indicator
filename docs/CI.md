# CI Quality (ASI-007)

| Field | Value |
|---|---|
| **Version** | `1.0.0` |
| **Status** | Active |
| **Last updated** | 2026-07-26 |
| **Workflow** | [`.github/workflows/ci.yml`](../.github/workflows/ci.yml) |
| **Local parity** | `make ci-local` · `make test-integrity` · `make test-arch` · `make test-smoke` |

## Gates (blocking)

1. **Repository integrity** — `scripts/ci_repository_integrity.py`  
   Discovery paths, imports, `__version__`, `__all__` resolve; orphan `data-ingestion` not registered.
2. **Architecture tests** — all `packages/*/tests/test_architecture*.py`
3. **Monorepo smoke** — `packages/dsp_platform/tests/test_asi_monorepo_smoke.py`
4. **Full package suite** — `pytest packages` with coverage XML
5. **Ruff / Black / mypy** — existing style and scoped typing gates

## Python versions

`3.11` and `3.12` (matrix). Runtime requires `>=3.11`.

## Dependencies

`pip install -e ".[dev]"` installs monorepo discovery paths plus FastAPI/Starlette/httpx/Pydantic for HTTP/security tests.

## Reporting

GitHub Actions job summary includes integrity / architecture / smoke / full-suite outcomes.
