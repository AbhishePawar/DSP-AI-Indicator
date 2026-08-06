# Changelog — DSP AI Indicator (commercial channel)

Format: Keep a Changelog-inspired · versions are platform commercial tags.

## [2.0.0] / backend 2.0.0 — 2026-07-29 (P8.0)

### Added

- GA architecture certification, technical debt register, release freeze policy
- `docs/P8_GENERAL_AVAILABILITY.md` and `scripts/ops/certify_p8.py`
- Platform audit of P1–P7 with living conditions retained

### Changed

- Frontend **2.0.0** · Backend **2.0.0** · channel **`ga-candidate`** · API contract label remains **v1.0.0**
- Engineering enters **RELEASE FREEZE** (hotfixes only)

### Unchanged

- Analytical engines and analyse behaviour

## [2.0.4] / backend 1.7.4 — 2026-07-29 (P7.4)

### Added

- Grafana operations dashboard + provisioning
- Prometheus alert rules + Alertmanager
- Postgres/Redis exporters in production compose
- DR pack: incremental backup, recovery validation, RPO/RTO docs
- Ops docs: dashboard, alerting, DR, runbook, logging, readiness, risk register
- `scripts/ops/certify_p7_4.py`

### Changed

- Frontend **2.0.4** · Backend **1.7.4** · API contract label remains **v1.0.0**

### Unchanged

- Analytical engines and analyse behaviour

## [2.0.3] / backend 1.7.3 — 2026-07-29 (P7.3)

### Added

- API latency benchmark, load test (10–500 users), and memory snapshot scripts (`scripts/perf/`)
- Performance docs: `PERFORMANCE_BACKEND.md`, `PERFORMANCE_FRONTEND.md`, `DATABASE_PERFORMANCE.md`
- `docs/P7_3_PERFORMANCE_REPORT.md` and `scripts/ops/certify_p7_3.py`

### Changed

- Frontend **2.0.3** · Backend **1.7.3** · API contract label remains **v1.0.0**
- Docker backend installs `.[api]` (not `[dev]`); `PYTHONOPTIMIZE=1`
- Uvicorn keep-alive / concurrency knobs; Next static cache + `optimizePackageImports`

### Unchanged

- Analytical engines and analyse behaviour

## [2.0.2] / backend 1.7.2 — 2026-07-29 (P7.2)

### Added

- Release engineering scripts (`validate_release`, `create_release_notes`, `build_release_package`)
- Repository / dependency / code quality / documentation / version governance audits
- `docs/ENGINEERING_STATUS.md` dashboard
- GitHub workflows: `release-engineering.yml`, `security.yml`
- `release/` package (notes, checklist, manifest, checksums, SBOM)
- `scripts/ops/certify_p7_2.py`

### Changed

- Frontend **2.0.2** · Backend **1.7.2** · API contract label remains **v1.0.0**

### Unchanged

- Analytical engines and analyse behaviour

## [2.0.0] / backend 1.7.0 — 2026-07-29 (P7.0)

### Added

- Production compose with Caddy HTTPS, Postgres, Redis, Prometheus, cAdvisor
- Deploy / rollback / backup / restore scripts
- `docs/P7_PRODUCTION_DEPLOYMENT.md` + `docs/P7_PRODUCTION_CERTIFICATION.md`

### Changed

- Frontend **2.0.0** · Backend **1.7.0** · API contract label **v1.0.0**
- Production env validation requires `DSP_DATABASE_URL` + `DSP_PUBLIC_DOMAIN`

### Unchanged

- Analytical engines and analyse behaviour

## [2.0.0-rc] / backend 1.6.0 — 2026-07-29 (P6.1)

### Added

- Product packaging & pricing docs; in-app `/docs/pricing`, `/docs/support`, `/docs/quick-start`, `/docs/faq`
- Operational runbooks (incident, outage, backup, deploy, rollback, security)
- Commercial readiness scorecard (`docs/P6_1_COMMERCIAL_READINESS.md`)
- Media kit placeholders; launch announcement draft; product overview

### Changed

- Frontend foundation **2.0.0-rc**; backend **1.6.0** (ops/commercial only)
- First-run onboarding copy for commercial RC

### Unchanged

- Engines, AI Committee, `/api/v1` analyse contracts

## [1.9.0] / backend 1.5.0 — 2026-07-29 (P5.2)

- Beta stabilisation RC: fail-closed invite gate, snapshots, RC assessment

## [1.8.0] / backend 1.4.0 — P5.1

- Closed beta programme surfaces

## Earlier

See `docs/RELEASE_NOTES_*.md` and `docs/VERSION_MATRIX.md`.
