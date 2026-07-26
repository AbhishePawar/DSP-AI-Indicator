# Release Engineering

| Field | Value |
|---|---|
| **Version** | `1.0.0` |
| **Status** | Active |
| **Last updated** | 2026-07-26 |
| **Epic** | REP-001 |
| **Authority** | Supplements [ASI_IMPLEMENTATION_FRAMEWORK.md](ASI_IMPLEMENTATION_FRAMEWORK.md) · [PACKAGE_GOVERNANCE.md](PACKAGE_GOVERNANCE.md) |

## Purpose

Behaviour-neutral release packaging, repository hygiene, and developer setup for
DSP AI Indicator after ASI closure.

---

## 1. Repository layout

```text
apps/web/          Thin Next.js client (presentation only)
packages/          Python monorepo domains + platform
scripts/           CI integrity + optional validation harnesses
docs/              Governance, ASI, release engineering
.github/workflows/ CI quality gates
configs/           Reserved configuration trees (if present)
data/              Local data planes (gitignored content)
tests/             Optional root test helpers
```

Canonical version truth → [VERSION_MATRIX.md](VERSION_MATRIX.md) · [DSP_STATUS.md](DSP_STATUS.md).

---

## 2. Developer setup

### Backend (Python ≥ 3.11)

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
pip install -e ".[dev]"
make test-integrity   # or: python scripts/ci_repository_integrity.py
make test-arch
make test-smoke
pytest packages --import-mode=importlib -p no:cov
```

### Web (`apps/web`)

```bash
cd apps/web
npm install
npm run dev
```

Never commit `.venv/`, `node_modules/`, or `.env` (see `.gitignore`).

---

## 3. Build process

| Surface | Command | Notes |
|---|---|---|
| Python packages | `pip install -e ".[dev]"` | Root discovers `packages/*/src` |
| Lint/type | `ruff` · `black --check` · `mypy` | Scoped mypy per `pyproject.toml` |
| CI local parity | `make ci-local` | Integrity + arch + smoke + suite + lint |
| Web production | `cd apps/web && npm run build` | Next.js build; outputs ignored |

---

## 4. Packaging policy (release archives)

Release archives / source distributions **MUST exclude**:

| Category | Examples |
|---|---|
| Virtual envs | `.venv/`, `venv/` |
| Caches | `.pytest_cache/`, `.ruff_cache/`, `.mypy_cache/`, `__pycache__/` |
| Coverage | `.coverage*`, `coverage.xml`, `htmlcov/` |
| Node | `node_modules/`, `.next/`, `out/`, `*.tsbuildinfo` |
| Build | `dist/`, `build/`, `*.egg-info/` |
| Secrets | `.env`, `.env.local` |
| Temp outputs | `pytest_out.txt`, `*.log`, `tmp/` |
| IDE | `.idea/`, `.vscode/` |

**Include:** source under `packages/`, `apps/web` (without caches), `docs/`,
`scripts/`, `pyproject.toml`, `Makefile`, `.github/workflows/`, `LICENSE`, `README.md`,
`VERSION`, `.env.example` (if present).

Suggested archive check:

```bash
git archive --format=zip --output=dsp-ai-indicator-src.zip HEAD
# Inspect zip: no .venv, node_modules, pytest_out, coverage, tsbuildinfo
```

---

## 5. Distribution checklist

- [ ] `git status` clean of generated artefacts  
- [ ] Integrity script PASS  
- [ ] Architecture + smoke PASS  
- [ ] No absolute local machine paths in tracked files  
- [ ] No empty placeholder infra files  
- [ ] `VERSION_MATRIX` / `DSP_STATUS` current  
- [ ] Tag/milestone named per release policy  

---

## 6. Repository cleanup checklist

- [ ] Caches ignored (see `.gitignore`)  
- [ ] No tracked `pytest_out.txt` / coverage dumps  
- [ ] No tracked `*.tsbuildinfo`  
- [ ] Debug harnesses live under `scripts/` only  
- [ ] Empty/unused compose/Docker placeholders removed or documented  

---

## 7. Optional scripts

| Script | Purpose |
|---|---|
| `scripts/ci_repository_integrity.py` | Registration / import integrity (CI) |
| `scripts/web_emi_validation.js` | Optional web EMI validation harness |

---

## 8. Deployment assets

| Asset | Status |
|---|---|
| `docker-compose.yml` | **Removed (REP-001)** — was empty placeholder; no compose stack shipped |
| Dockerfiles | **None** in repository |
| Makefile | Local/CI parity targets only |

Do **not** invent infrastructure in release engineering tasks.

---

## 9. Dependency governance (summary)

| Layer | Ownership |
|---|---|
| Root `pyproject.toml` | Monorepo meta + shared `dev` tooling + HTTP test extras |
| Package `pyproject.toml` | Declared first-party runtime deps (evidence-based) |
| `apps/web/package.json` | Web runtime/dev deps only |

Package-level dependencies are intentional and are **not** consolidated into the root
runtime set (ASI-004 / Package Governance). Root `dependencies` remain minimal (`numpy`).

---

## Related

[REP_001_REPOSITORY_CLEANUP.md](REP_001_REPOSITORY_CLEANUP.md) · [CI.md](CI.md) ·
[PACKAGE_GOVERNANCE.md](PACKAGE_GOVERNANCE.md)
