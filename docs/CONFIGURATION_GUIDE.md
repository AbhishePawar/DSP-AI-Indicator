# Configuration Guide (PEP-002)

Typed configuration lives in `production_platform.ProductionConfiguration`.
Load from environment via `load_configuration_from_environ()`.

## Profiles

| `DSP_ENVIRONMENT` | Meaning |
|---|---|
| `development` | Local defaults; in-memory OK |
| `test` | CI / contract tests |
| `staging` | India staging with Postgres/Redis |
| `production` | Non-local `DSP_REGION` required |

## Core variables

| Variable | Purpose | Default |
|---|---|---|
| `DSP_ENVIRONMENT` | Profile | `development` |
| `DSP_SERVICE_NAME` | Service identity | `dsp-ai-indicator` |
| `DSP_SERVICE_VERSION` | Service version | `0.2.0` |
| `DSP_REGION` | Deploy region | `local` (prod → e.g. `ap-south-1`) |
| `DSP_LOG_LEVEL` | Log level | `INFO` |
| `DSP_DATABASE_URL` | Postgres DSN | unset → memory |
| `DSP_REDIS_URL` | Redis URL | unset → memory |
| `DSP_REDIS_FALLBACK` | Degrade to memory if Redis down | `true` |
| `DSP_OBJECT_STORAGE_PROVIDER` | `memory` \| `local` \| `s3` \| `minio` \| `azure` \| `gcs` | `memory` |
| `DSP_OBJECT_STORAGE_BUCKET` | Bucket name | — |
| `DSP_OBJECT_STORAGE_ENDPOINT` | MinIO / custom endpoint | — |
| `DSP_OBJECT_STORAGE_LOCAL_ROOT` | Local FS root | — |
| `DSP_JOB_QUEUE_BACKEND` | `memory` (others reserved) | `memory` |
| `DSP_INDIA_TIMEZONE` | Presentation TZ | `Asia/Kolkata` |
| `DSP_INDIA_CURRENCY` | Presentation currency | `INR` |
| `DSP_CERT_IN_LOG_RETENTION_DAYS` | Must be ≥180 | `180` |

## Authenticated market quotes (EPIC-D001)

| Variable | Purpose | Default |
|---|---|---|
| `DSP_MARKET_QUOTE_API_KEY` | API key for HTTP / memory quote adapters | unset |
| `DSP_MARKET_QUOTE_BASE_URL` | Licensed vendor quote endpoint (with API key → HTTP adapter) | unset |
| `DSP_MARKET_QUOTE_MEMORY` | `true`/`1`/`yes` → in-memory authenticated adapter (seeded ops/tests only) | unset |

When unset, the **null** adapter is used: quotes are always `"Data unavailable."` (CV-001 safe default).

Docs: [EPIC_D001_AUTHENTICATED_MARKET_DATA.md](EPIC_D001_AUTHENTICATED_MARKET_DATA.md) · [EPIC_D001_MARKET_DATA_PROVIDER.md](EPIC_D001_MARKET_DATA_PROVIDER.md) · [EPIC_D001_OPERATIONS.md](EPIC_D001_OPERATIONS.md).

## Authenticated financial statements (EPIC-D002)

| Variable | Purpose | Default |
|---|---|---|
| `DSP_FINANCIAL_STATEMENT_API_KEY` | API key for HTTP / memory statement adapters | unset |
| `DSP_FINANCIAL_STATEMENT_BASE_URL` | Licensed vendor statements endpoint (with API key → HTTP adapter) | unset |
| `DSP_FINANCIAL_STATEMENT_MEMORY` | `true`/`1`/`yes` → in-memory authenticated adapter (seeded ops/tests only) | unset |

When unset, the **null** adapter is used: statements are always `"Data unavailable."` (CV-001 safe default).

Docs: [EPIC_D002_AUTHENTICATED_FINANCIAL_STATEMENTS.md](EPIC_D002_AUTHENTICATED_FINANCIAL_STATEMENTS.md) · [EPIC_D002_PROVIDER_GUIDE.md](EPIC_D002_PROVIDER_GUIDE.md) · [EPIC_D002_OPERATIONS.md](EPIC_D002_OPERATIONS.md).

## Authenticated corporate actions (EPIC-D003)

| Variable | Purpose | Default |
|---|---|---|
| `DSP_CORPORATE_ACTIONS_API_KEY` | API key for HTTP / memory corporate action adapters | unset |
| `DSP_CORPORATE_ACTIONS_BASE_URL` | Licensed vendor corporate actions endpoint | unset |
| `DSP_CORPORATE_ACTIONS_MEMORY` | `true`/`1`/`yes` → in-memory authenticated adapter | unset |

When unset, the **null** adapter is used: events are always `"Data unavailable."`

Docs: [EPIC_D003_AUTHENTICATED_CORPORATE_ACTIONS.md](EPIC_D003_AUTHENTICATED_CORPORATE_ACTIONS.md) · [EPIC_D003_PROVIDER_GUIDE.md](EPIC_D003_PROVIDER_GUIDE.md) · [EPIC_D003_OPERATIONS.md](EPIC_D003_OPERATIONS.md).

## Authenticated historical series (EPIC-D004)

| Variable | Purpose | Default |
|---|---|---|
| `DSP_HISTORICAL_SERIES_API_KEY` | API key for HTTP / memory historical adapters | unset |
| `DSP_HISTORICAL_SERIES_BASE_URL` | Licensed vendor historical series endpoint | unset |
| `DSP_HISTORICAL_SERIES_MEMORY` | `true`/`1`/`yes` → in-memory authenticated adapter | unset |

When unset, the **null** adapter is used: history is always `"Data unavailable."`

Docs: [EPIC_D004_AUTHENTICATED_HISTORICAL_SERIES.md](EPIC_D004_AUTHENTICATED_HISTORICAL_SERIES.md) · [EPIC_D004_PROVIDER_GUIDE.md](EPIC_D004_PROVIDER_GUIDE.md) · [EPIC_D004_OPERATIONS.md](EPIC_D004_OPERATIONS.md).

## Unified data gateway (EPIC-D005)

No additional env vars. The orchestrator aggregates D001–D004 providers configured
above. Routes: `GET /api/v1/data/bundle`, `GET /api/v1/data/health`.

Docs: [EPIC_D005_UNIFIED_DATA_ORCHESTRATOR.md](EPIC_D005_UNIFIED_DATA_ORCHESTRATOR.md) · [EPIC_D005_ORCHESTRATOR_DESIGN.md](EPIC_D005_ORCHESTRATOR_DESIGN.md) · [EPIC_D005_OPERATIONS.md](EPIC_D005_OPERATIONS.md).

## Research Object (EPIC-R001)

No additional env vars. Aggregates D005 + existing analysis payloads only.
Routes: `GET /api/v1/research/object/schema`, `POST /api/v1/research/object`.

Docs: [EPIC_R001_README.md](EPIC_R001_README.md) · [EPIC_R001_RESEARCH_OBJECT_SPEC.md](EPIC_R001_RESEARCH_OBJECT_SPEC.md) · [EPIC_R001_DEVELOPER_GUIDE.md](EPIC_R001_DEVELOPER_GUIDE.md).

## Institutional Research Report (EPIC-R002)

No additional env vars. Generates reports from Research Object dicts only.
Routes: `GET /api/v1/research/report/schema`, `POST /api/v1/research/report`.

Docs: [EPIC_R002_README.md](EPIC_R002_README.md) · [EPIC_R002_REPORT_SPEC.md](EPIC_R002_REPORT_SPEC.md) · [EPIC_R002_DEVELOPER_GUIDE.md](EPIC_R002_DEVELOPER_GUIDE.md).

## Institutional Export (EPIC-R003)

No additional env vars. Exports Institutional Report dicts only
(`json` / `csv` / `xlsx` / `pdf`).
Routes: `GET /api/v1/research/export/schema`, `POST /api/v1/research/export`.

Docs: [EPIC_R003_README.md](EPIC_R003_README.md) · [EPIC_R003_EXPORT_SPEC.md](EPIC_R003_EXPORT_SPEC.md) · [EPIC_R003_OPERATIONS.md](EPIC_R003_OPERATIONS.md).

## Research Archive (EPIC-R004)

No additional env vars. Default in-memory immutable archive.
Routes: `/api/v1/research/archive/*` (schema, snapshots, history, compare, retention).

Docs: [EPIC_R004_README.md](EPIC_R004_README.md) · [EPIC_R004_ARCHIVE_SPEC.md](EPIC_R004_ARCHIVE_SPEC.md) · [EPIC_R004_OPERATIONS.md](EPIC_R004_OPERATIONS.md).

## Research Diff (EPIC-R005)

No additional env vars. Structural comparison of archived snapshots only.
Routes: `GET /api/v1/research/diff/schema`, `POST /api/v1/research/diff`.

Docs: [EPIC_R005_README.md](EPIC_R005_README.md) · [EPIC_R005_DIFF_SPEC.md](EPIC_R005_DIFF_SPEC.md) · [EPIC_R005_OPERATIONS.md](EPIC_R005_OPERATIONS.md).

## AI Research Copilot (EPIC-A001)

No additional env vars. Grounded Q&A over research artifacts only (no providers).
Routes: `GET /api/v1/research/copilot/schema`, `POST /api/v1/research/copilot/ask`.

Docs: [EPIC_A001_README.md](EPIC_A001_README.md) · [EPIC_A001_COPILOT_GUIDE.md](EPIC_A001_COPILOT_GUIDE.md) · [EPIC_A001_OPERATIONS.md](EPIC_A001_OPERATIONS.md).

## Portfolio Intelligence (EPIC-A002)

No additional env vars. Summarizes portfolios/watchlists via linked Research Objects.
Routes: `GET /api/v1/portfolio/intelligence/schema`, `POST /api/v1/portfolio/intelligence`.

Docs: [EPIC_A002_README.md](EPIC_A002_README.md) · [EPIC_A002_PORTFOLIO_GUIDE.md](EPIC_A002_PORTFOLIO_GUIDE.md) · [EPIC_A002_OPERATIONS.md](EPIC_A002_OPERATIONS.md).

## Continuous Research Monitoring (EPIC-A003)

No additional env vars. Detects changes via R004/R005 and supplied A002 results.
Routes: `GET /api/v1/research/monitoring/schema`, `POST /api/v1/research/monitoring/{watchlist,portfolio,track,evaluate}`.

Docs: [EPIC_A003_README.md](EPIC_A003_README.md) · [EPIC_A003_MONITORING_GUIDE.md](EPIC_A003_MONITORING_GUIDE.md) · [EPIC_A003_OPERATIONS.md](EPIC_A003_OPERATIONS.md).

## Institutional Decision Workspace (EPIC-A004)

No additional env vars. Aggregates supplied R001–R005 / A001–A003 artifacts.
Routes: `GET /api/v1/decision/workspace/schema`, `POST /api/v1/decision/workspace`.

Docs: [EPIC_A004_README.md](EPIC_A004_README.md) · [EPIC_A004_WORKSPACE_GUIDE.md](EPIC_A004_WORKSPACE_GUIDE.md) · [EPIC_A004_OPERATIONS.md](EPIC_A004_OPERATIONS.md).

## Institutional Multi-Agent Committee (EPIC-A005)

No additional env vars. Deterministic multi-agent review of supplied artifacts.
Routes: `GET /api/v1/committee/schema`, `GET /api/v1/committee/agents`, `POST /api/v1/committee/run`.

Docs: [EPIC_A005_README.md](EPIC_A005_README.md) · [EPIC_A005_AGENT_GUIDE.md](EPIC_A005_AGENT_GUIDE.md) · [EPIC_A005_OPERATIONS.md](EPIC_A005_OPERATIONS.md).

## Investment Policy & Compliance (EPIC-A006)

No additional env vars. Deterministic policy evaluation over supplied artifacts.
Routes: `GET /api/v1/policy/schema`, `GET /api/v1/policy/default`, `POST /api/v1/policy/evaluate`.

Docs: [EPIC_A006_README.md](EPIC_A006_README.md) · [EPIC_A006_RULE_SPECIFICATION.md](EPIC_A006_RULE_SPECIFICATION.md) · [EPIC_A006_OPERATIONS.md](EPIC_A006_OPERATIONS.md).

## Institutional Workflow & Approval (EPIC-A007)

No additional env vars. Manages workflow state only (no research mutation).
Routes: `GET /api/v1/workflow/schema`, `GET /api/v1/workflow/templates`, `POST /api/v1/workflow/action`.

Docs: [EPIC_A007_README.md](EPIC_A007_README.md) · [EPIC_A007_WORKFLOW_GUIDE.md](EPIC_A007_WORKFLOW_GUIDE.md) · [EPIC_A007_OPERATIONS.md](EPIC_A007_OPERATIONS.md).

## Institutional Persistence Layer (EPIC-A008)

No additional env vars. In-memory storage provider by default (A008-ready for future DBs).
Routes: `GET /api/v1/persistence/schema`, `POST /api/v1/persistence/{entity,workflow,snapshot}`, `GET /api/v1/persistence/entity/{kind}/{id}`.

Docs: [EPIC_A008_README.md](EPIC_A008_README.md) · [EPIC_A008_PERSISTENCE_ARCHITECTURE.md](EPIC_A008_PERSISTENCE_ARCHITECTURE.md) · [EPIC_A008_DEVELOPER_GUIDE.md](EPIC_A008_DEVELOPER_GUIDE.md).

## Institutional Authentication & RBAC (EPIC-A009)

Optional env: `DSP_AUTH_JWT_SECRET` (defaults to dev secret when unset — replace in production).
Routes: `GET/POST /api/v1/auth/rbac/*` (schema, login, logout, refresh, me, users, roles, permissions, evaluate, protect).
Legacy `POST /api/v1/auth/login` unchanged.

Docs: [EPIC_A009_README.md](EPIC_A009_README.md) · [AUTH_ARCHITECTURE.md](AUTH_ARCHITECTURE.md) · [RBAC_GUIDE.md](RBAC_GUIDE.md) · [SECURITY_GUIDE.md](SECURITY_GUIDE.md) · [API_GUIDE.md](API_GUIDE.md) · [DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md).

## Enterprise Administration & Audit Console (EPIC-A010)

No required env vars. Read-only console over A008/A009 artifacts.
Routes: `GET/POST /api/v1/admin/*` (schema, dashboard, users, roles, permissions, sessions, audit, export, workflow-history, research-archive, timeline, search, health, configuration, versions, feature-flags, metrics).

Docs: [EPIC_A010_README.md](EPIC_A010_README.md) · [EPIC_A010_ADMIN_ARCHITECTURE.md](EPIC_A010_ADMIN_ARCHITECTURE.md) · [EPIC_A010_OPERATIONS_GUIDE.md](EPIC_A010_OPERATIONS_GUIDE.md) · [EPIC_A010_SECURITY_GUIDE.md](EPIC_A010_SECURITY_GUIDE.md) · [EPIC_A010_DEVELOPER_GUIDE.md](EPIC_A010_DEVELOPER_GUIDE.md).

## Production Certification (EPIC-V100)

No behavioural config changes. `dsp_platform` promoted to **1.0.0**.
Docs: [EPIC_V100_README.md](EPIC_V100_README.md) · [EPIC_V100_PRODUCTION_CERTIFICATION.md](EPIC_V100_PRODUCTION_CERTIFICATION.md) · [EPIC_V100_RELEASE_NOTES.md](EPIC_V100_RELEASE_NOTES.md) · [EPIC_V100_MIGRATION_GUIDE.md](EPIC_V100_MIGRATION_GUIDE.md) · [EPIC_V100_COMPATIBILITY_MATRIX.md](EPIC_V100_COMPATIBILITY_MATRIX.md).

## Frontend Foundation (… + ARCH-002 + P2.1 + P2.2 + P2.3)

Architecture freeze through Frontend Production Release, plus Buffett report,
Institutional Ratings, Report Transparency (P2.1), Explainability Framework
(P2.2), and **Valuation Transparency (P2.3)** — presentation only.
App **v1.5.0**.

## Backend Operations (P1.2 + P1.3)

`dsp_platform` **1.2.0** — security hardening (P1.2) and monitoring/reliability
(P1.3). Analysis contracts unchanged.

Docs: [P1_2_SECURITY_HARDENING_AUDIT.md](P1_2_SECURITY_HARDENING_AUDIT.md) ·
[P1_3_MONITORING_AND_RELIABILITY.md](P1_3_MONITORING_AND_RELIABILITY.md) ·
[ARCH_002_INSTITUTIONAL_RATING_FRAMEWORK.md](ARCH_002_INSTITUTIONAL_RATING_FRAMEWORK.md) ·
[P2_1_REPORT_TRANSPARENCY.md](P2_1_REPORT_TRANSPARENCY.md) ·
[P2_2_EXPLAINABILITY_FRAMEWORK.md](P2_2_EXPLAINABILITY_FRAMEWORK.md) ·
[P2_3_VALUATION_TRANSPARENCY.md](P2_3_VALUATION_TRANSPARENCY.md).

## Secrets

`EnvSecretsPort` reads `DSP_SECRET_<NAME>` (never logged).

Future secret managers (AWS Secrets Manager, Azure Key Vault, HashiCorp Vault)
implement the same `SecretProviderPort` / `SecretsPort` protocol.

## Validation

```python
from production_platform import ConfigurationManager, load_configuration_from_environ

cfg = load_configuration_from_environ()
ConfigurationManager(cfg).validate()
```

Production profile rejects `region=local`.
