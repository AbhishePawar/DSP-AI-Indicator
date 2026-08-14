# Workflow Automation Guide (RC1 Milestone 5)

Status: **COMPLETE** (with recorded gaps — see below)
Priority: P1 · Workflow Automation
Related: [PORTFOLIO_GUIDE.md](PORTFOLIO_GUIDE.md#portfolio-intelligence-engine-rc1-milestone-4)
(Portfolio Intelligence Engine — frozen, reused for valuation alerts and
scheduled report content), [PORTFOLIO_ANALYTICS.md](PORTFOLIO_ANALYTICS.md)
(quantitative engine — frozen, reused transitively), [API_GUIDE.md](API_GUIDE.md#workflow-automation-api-rc1-milestone-5)
(endpoint reference), [DSP_AI_INDICATOR_ARCHITECTURE.md](DSP_AI_INDICATOR_ARCHITECTURE.md#87-workflow-automation-rc1-milestone-5)
(architecture addendum, §8.7)

## Goal

Add **Alert Rules** (Price / Valuation / Research Refresh / Earnings),
**Scheduled Reports**, and a **Notification Center** — orchestrating
existing, frozen engines to evaluate rules and produce report content.
**No new valuation, risk, market-data, or notification-delivery engine was
built.**

## Why this is not `packages/workflow`

`packages/workflow` (H1.0–H1.3) already exists and is **Production ·
Frozen** — but it is a *different* capability: research-pipeline
orchestration (`WorkflowProfile`/`WorkflowStep`/`WorkflowEngine`) with an
explicit "never schedules work, never persists" contract. It has nothing to
do with product-facing alerts, scheduled reports, or a notification inbox.
Similarly, EPIC-A007's `/workflow/schema` · `/workflow/templates` ·
`/workflow/action` routes are institutional **approval workflow**
(draft → review → published), also unrelated. This milestone's package is
named `workflow_automation` and its API is mounted at
**`/workflow-automation`** to avoid any confusion with either.

## What already existed vs. what is genuinely new

| Capability | Existing engine reused | New in this milestone |
|---|---|---|
| Price Alerts | `dsp_platform.market_quotes.get_authenticated_market_quote` (Data Connector Framework, frozen) | Rule persistence + a pure threshold comparison (`evaluate_price_alert`) |
| Valuation Alerts | `dsp_platform.portfolio_intelligence_engine` (RC1 Milestone 4, frozen) + `dsp_platform.portfolio_store_facade` (RC1 Milestone 3, frozen) for holdings | Rule persistence + a pure classification-match comparison (`evaluate_valuation_alert`) |
| Research Refresh Alerts | None — simple date arithmetic on a caller-supplied "last analysed at" timestamp | Rule persistence + a pure date-difference comparison (`evaluate_research_stale_alert`) |
| Earnings Alerts | **None exist anywhere in the platform** — no earnings-calendar Data Connector Framework provider | Rule *schema* only, forward-extensible; evaluation is **always** `Data unavailable.` (`evaluate_earnings_alert`) — never fabricated |
| Scheduled Reports | `dsp_platform.portfolio_intelligence_engine` + `portfolio_store_facade` (same as valuation alerts) for content | Schedule *definition* persistence + a `run_now` action; **no autonomous scheduler** (see below) |
| Notification Center | `auth.email_delivery.EmailProviderPort` (existing password-reset/invite email infrastructure) for optional delivery | Durable per-user notification log + read/unread state |

## Architecture

```mermaid
flowchart TB
    subgraph Caller["Caller (frontend "Check now" / "Run now", or an external cron hitting the API)"]
        UI["Workflow Automation Workspace (/workflow)"]
    end

    subgraph API["api_platform.routers.workflow_automation (thin)"]
        R1["/workflow-automation/alerts (CRUD)"]
        R2["/workflow-automation/alerts/evaluate"]
        R3["/workflow-automation/schedules (CRUD)"]
        R4["/workflow-automation/schedules/{id}/run"]
        R5["/workflow-automation/notifications"]
    end

    subgraph Facade["dsp_platform.workflow_automation (orchestration)"]
        Eval["evaluate_user_alerts()\n— the only place engine calls happen"]
        Run["run_scheduled_report_now()"]
    end

    subgraph Reused["Reused, frozen engines"]
        MQ["market_quotes\n(Data Connector Framework)"]
        PIE["portfolio_intelligence_engine\n(RC1 Milestone 4)"]
        PS["portfolio_store_facade\n(RC1 Milestone 3)"]
        Email["auth.email_delivery.EmailProviderPort"]
    end

    subgraph Store["workflow_automation (new, persistence + pure evaluation)"]
        Svc["WorkflowAutomationService\n(ownership-checked CRUD)"]
        PureEval["evaluation.py\n(pure comparison functions)"]
    end

    UI --> R1 & R2 & R3 & R4 & R5
    R1 & R3 & R5 --> Svc
    R2 --> Eval
    R4 --> Run
    Eval --> MQ
    Eval --> PIE
    Eval --> PS
    Eval --> PureEval
    Eval --> Svc
    Eval -. "on trigger only" .-> Email
    Run --> PIE
    Run --> PS
    Run --> Svc
```

- **`packages/workflow_automation`** — mirrors `packages/portfolio_store`'s
  exact architecture: a `WorkflowAutomationStorePort` Protocol, an
  `InMemoryWorkflowAutomationStore` default, and a
  `DatabaseWorkflowAutomationStore` that hydrates from / flushes to a
  `production_platform.DatabasePort` (duck-typed, zero import dependency).
  `evaluation.py` holds pure comparison functions only — no I/O.
- **`dsp_platform.workflow_automation`** — the *only* orchestration layer.
  `evaluate_user_alerts()` fetches the already-computed signal from the
  matching frozen engine per rule type, calls the pure comparison, and —
  only on a transition into `"triggered"` — creates a Notification and
  best-effort sends an email via the existing `EmailProviderPort`.
  `run_scheduled_report_now()` reuses the Portfolio Intelligence Engine to
  build a snapshot and serializes it (pure JSON/CSV formatting, not a new
  export engine).
- **`api_platform.routers.workflow_automation`** — ten thin, authenticated
  routes, each only calling the matching `DSPPlatform` method.

## Notification persistence — a deliberate design choice, not a limitation

`portfolio_store`'s Transaction ledger is genuinely append-only (never
mutated). A Notification's `read_at` *is* mutated after creation, and the
shared `InMemoryDatabasePort` test adapter's minimal SQL dialect supports
only `CREATE TABLE` / `INSERT INTO` / `DELETE FROM` (whole-table) /
`SELECT` — no `UPDATE`, no row-scoped `DELETE`. So notifications are stored
in the same per-user, rewrite-on-each-flush JSON snapshot as alert
rules/scheduled reports, rather than a separate append-only table — the
correct data-store choice for a field that changes after creation.

## No autonomous scheduler (recorded gap, not silently worked around)

`dsp_platform` cannot import `production_platform`'s `SchedulerPort` /
`JobQueuePort` — this is a **forbidden import**, enforced by
`packages/dsp_platform/tests/test_boundaries.py`. Even if it could, those
ports are explicitly documented as in-memory/process-local ("not Celery /
RQ", "not Celery / SQS") — not restart-safe. Building a durable,
production-grade scheduler is a distinct, infrastructure-level piece of
work, out of scope for an orchestration-only milestone. What **is**
implemented:

- Alert rules are evaluated **on demand** — via the frontend's "Check now"
  button, or by an external caller (e.g. a real cron job) hitting
  `POST /workflow-automation/alerts/evaluate` on a schedule of its own.
- Scheduled Report *definitions* persist a declared cadence
  (`daily`/`weekly`/`monthly`), but nothing fires them automatically —
  `POST /workflow-automation/schedules/{id}/run` ("Run now") is the only
  implemented execution path today.

## Earnings Alerts — honestly unavailable, not fabricated

No Data Connector Framework provider for an earnings calendar exists
anywhere in the platform (confirmed absent from `data_engine`'s six
existing connector domains — News, Filings, Ownership, Insider Trading,
ESG, Transcripts). `evaluate_earnings_alert()` always returns
`AlertStatus.UNAVAILABLE` with an explicit `"Data unavailable."` message.
The rule type exists in the schema only so a future earnings-calendar
connector can be wired in without a schema migration — consistent with
CV-001 (no fabricated numbers).

## API

See [API_GUIDE.md](API_GUIDE.md#workflow-automation-api-rc1-milestone-5)
for the full request/response reference.

| Method | Path | Purpose |
|---|---|---|
| GET | `/workflow-automation/schema` | Schema descriptor — no auth required |
| GET | `/workflow-automation/health` | Service health — no auth required |
| GET/POST | `/workflow-automation/alerts` | List / create alert rules |
| GET/PUT/DELETE | `/workflow-automation/alerts/{id}` | Get / update / delete one rule |
| POST | `/workflow-automation/alerts/evaluate` | On-demand evaluation trigger |
| GET/POST | `/workflow-automation/schedules` | List / create scheduled report definitions |
| GET/PUT/DELETE | `/workflow-automation/schedules/{id}` | Get / update / delete one schedule |
| POST | `/workflow-automation/schedules/{id}/run` | Run a schedule now |
| GET | `/workflow-automation/notifications` | List the user's notifications |
| POST | `/workflow-automation/notifications/{id}/read` | Mark one notification read |

## Frontend

New route `/workflow` (`WorkflowAutomationWorkspace`) with three tabs —
Alert Rules, Scheduled Reports, Notifications — using the existing design
system (`Tabs`, `Card`, `Badge`, `Select`, `EmptyState`). No redesign; the
workspace shell mirrors `/portfolio`'s `ProtectedRoute` + `PageHeader`
convention exactly.

## Testing

- `packages/workflow_automation/tests/` — 46 unit tests (evaluation
  functions, ownership-checked CRUD, database-store durability including a
  rehydrate-across-restart test).
- `packages/dsp_platform/tests/test_workflow_automation.py` — 17
  orchestration tests, mocking only at the exact reused-engine boundary
  (`market_quotes`, `portfolio_intelligence_engine`) — never re-deriving a
  price or valuation number itself.
- `packages/api_platform/tests/test_workflow_automation_api.py` — 12 API
  tests (authentication required, ownership 403s, validation 400s,
  evaluate → notification flow, scheduled run-now).
- `apps/web/src/lib/workflow-automation/mapWorkflowAutomation.test.ts` — 14
  mapper tests.
- `apps/web/src/components/workflow-automation/*.test.tsx` — 11 component
  tests across all three panels.
- `apps/web/e2e/browser/workflow-automation.smoke.spec.ts` — Playwright
  structural smoke test.

## Performance

- Price alerts call `get_authenticated_market_quote` once per unique
  symbol per evaluation pass (already has its own resilience/caching from
  the Data Connector Framework — no new caching layer added).
- Valuation alerts group by `portfolio_id` and call the Portfolio
  Intelligence Engine **once per unique portfolio**, not once per rule —
  multiple rules against the same portfolio share one evaluation.
- Notifications are only created on a **transition** into `"triggered"`
  (never on every re-evaluation of an already-triggered rule) — prevents
  notification spam from repeated "Check now" clicks.

## Security review

- Every route (except the two public schema/health descriptors) requires
  authentication via the existing `get_current_user_id` dependency — no new
  auth scheme.
- Ownership is checked on every single operation, mirroring
  `portfolio_store`'s exact pattern — verified by dedicated 403 tests.
- Email delivery is best-effort and swallows its own failures (a
  notification is always recorded first, regardless of whether email
  sending succeeds) — a delivery failure never masks or blocks the
  underlying alert record.

## Remaining gaps (recorded honestly, not silently worked around)

- **No autonomous scheduler.** See "No autonomous scheduler" above —
  evaluation and schedule execution are both caller-driven today.
- **No earnings-calendar data source.** Earnings Alerts are schema-only and
  always report unavailable until a real connector exists.
- **No transaction/lot-aware alerts.** Alert rules operate on a portfolio's
  current holdings (via `portfolio_store_facade`), not on unrealized
  gain/loss or tax-lot state (`portfolio_analytics`'s Tax Optimization
  module is a separate, already-existing capability, not wired into
  alerting here).
- **Email recipient is caller-supplied per rule** (`params.notify_email`),
  not automatically resolved from the user's account profile — resolving a
  user's own verified email would require reaching into `auth` internals
  beyond the existing `EmailProviderPort` contract, deferred to keep this
  milestone orchestration-only.
- **CSV serialization for Scheduled Reports covers the Valuation Heatmap
  only** — a deliberately small, honest starting slice; extending it to
  every Portfolio Intelligence Engine section is straightforward additive
  work for a future milestone.
