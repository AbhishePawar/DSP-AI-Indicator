# 08 — Dependency Report

Snapshot guidance for auditors. Exact lockfile contents are copied into `configs/`. Regenerating the package refreshes versions from the live tree.

---

## Frontend (`apps/web`)

| Item | Location |
|---|---|
| Manifest | `configs/web/package.json` |
| Lockfile | `configs/web/package-lock.json` (if present) |
| Framework | Next.js 15.x · React 19.x |
| Test | Vitest (+ Testing Library, vitest-axe patterns) |
| Styling | Tailwind via `@tailwindcss/postcss` / `postcss.config.mjs` |
| State / data | Zustand, TanStack Query/Table |
| Charts | ECharts (presentation only) |

**Audit note:** UI libraries must not implement valuation/recommendation engines. Dependency presence ≠ analytical ownership.

---

## Backend / monorepo Python

| Item | Location |
|---|---|
| Root project | `configs/root/pyproject.toml` |
| Per-package | `source/packages/<name>/pyproject.toml` |
| Requires-Python | `>=3.11` (root) |
| Typical API stack | FastAPI, Starlette, Pydantic, Uvicorn, HTTPX (optional extras) |

Engine packages are first-party under `packages/*`. Prefer reviewing first-party research code and `dsp_platform` composition over third-party ML black boxes for CV/RS compliance.

---

## CI / automation dependencies

Workflows under `workflows/` (from `.github/workflows/`):

- `frontend.yml` — web lint/test/build gates
- `ci.yml` / `docker.yml` / `security.yml`
- `release.yml` / `release-engineering.yml`

Treat workflow pins and cache keys as part of reproducibility evidence.

---

## Supply-chain / secrets hygiene

| Check | Expectation |
|---|---|
| `.env` / secrets | **Not** in audit package (excluded) |
| `.env.example` | May be included as non-secret templates |
| `node_modules` / `.venv` | **Excluded** — regenerate locally |
| License | Root `LICENSE` copied under `docs/root/` |

---

## How to refresh this narrative with facts

1. Run the generator.
2. Open `manifests/DEPENDENCY_SUMMARY.md` (auto-generated).
3. Diff `configs/web/package.json` and root/package `pyproject.toml` files for version pins.
