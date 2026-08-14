# workflow_automation

**RC1 Milestone 5 — Workflow Automation.**

Server-side, user-owned persistence and evaluation logic for **Alert
Rules**, **Scheduled Reports**, and the **Notification Center** —
following the exact same architecture `packages/portfolio_store` (RC1
Milestone 3) already established: a `WorkflowAutomationStorePort`
Protocol with an `InMemoryWorkflowAutomationStore` default and a
`DatabaseWorkflowAutomationStore` that hydrates from / flushes to a
`production_platform.DatabasePort` (duck-typed, zero import dependency).

## What this package is

1. **Alert Rules** — a user-owned rule (`price`, `valuation`, `research_stale`,
   or `earnings`) that is *evaluated* against an already-computed signal from
   an existing, frozen engine — never a new calculation:
   - `price_above` / `price_below` — evaluated against
     `dsp_platform.get_authenticated_market_quote` (Data Connector Framework,
     frozen).
   - `valuation_flip` — evaluated against the Portfolio Intelligence
     Engine's `valuation_heatmap` (RC1 Milestone 4, frozen).
   - `research_stale` — a simple date-difference check against a
     caller-supplied "last analysed at" timestamp (no new staleness engine).
   - `earnings_upcoming` — **always evaluates to unavailable**. No earnings
     calendar data source exists anywhere in the platform (confirmed absent
     from the Data Connector Framework); this package does not invent one.
     The rule type exists so the schema is forward-extensible once a real
     earnings-calendar connector is added.
2. **Scheduled Reports** — a user-owned schedule *definition*
   (frequency/portfolio/format). **This package does not implement a cron
   engine.** `dsp_platform` has no access to `production_platform`'s
   scheduler ports (forbidden import, enforced by
   `dsp_platform.tests.test_boundaries`), so autonomous, restart-safe
   execution is out of scope here — see "Remaining gaps" in
   `docs/WORKFLOW_AUTOMATION_GUIDE.md`. What *is* implemented: a `run_now`
   action that reuses the existing Portfolio Analytics / Portfolio
   Intelligence Engine outputs and serializes them (no new export engine).
3. **Notification Center** — a durable, per-user notification log (stored
   alongside alert rules/scheduled reports in the same per-user JSON
   snapshot — not a separate append-only table, since `read_at` is mutated
   after creation and the shared `InMemoryDatabasePort` test adapter has no
   `UPDATE`/row-scoped `DELETE` support). Delivery (email) reuses the
   existing `auth.email_delivery.EmailProviderPort` — no new email/SMS/push
   infrastructure.

## What this package is not

- Not a valuation, risk, or scoring engine — see `evaluation.py`, which only
  compares already-computed values against caller-declared thresholds.
- Not a scheduler/cron/worker service.
- Not a new notification delivery channel.
