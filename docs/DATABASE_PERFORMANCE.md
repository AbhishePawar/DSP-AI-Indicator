# Database Performance — EPIC-P7.3

**Date:** 2026-07-29  
**Scope:** Review only — **no schema / migration behaviour changes**.

## Topology (P7 production)

- PostgreSQL 16 (compose) with persistent volume  
- Redis 7 AOF for cache/session/rate-limit ports when configured  
- API connects via `DSP_DATABASE_URL`

## Findings

| Area | Assessment |
|---|---|
| Connection pooling | Prefer pooler (PgBouncer) or SQLAlchemy/async pool in app adapters when DB-heavy paths scale; health probes do not stress DB |
| Indexes | Domain schemas owned by persistence packages — no P7.3 index rewrites (would risk behaviour) |
| Slow queries | No analyse/load DB benchmarks in this epic (engines frozen). Ops path is health/metrics. |
| Transactions | Keep short transactions; avoid holding locks across external provider calls |
| Migrations | Validate with existing persistence migration tooling before deploy; P7.3 adds no new migrations |

## Recommendations

1. Enable Postgres `log_min_duration_statement` (e.g. 200ms) in staging.  
2. Add read replicas only if report/history read fan-out requires it (future epic).  
3. Keep Redis for distributed rate limits before raising uvicorn workers.

**Database performance score:** **7.8 / 10** (review complete; tuning deferred without schema changes)
