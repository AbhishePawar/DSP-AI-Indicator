# Epic V2.0 Sprint 1 — Advisor Platform Foundation

**Web:** `2.0.0`

## Mission

Optional advisor architecture layer on top of stable Web 1.0.0. Domain foundation only — demo data, no persistence, no engine coupling.

## Enable

```bash
# apps/web/.env.local
NEXT_PUBLIC_ADVISOR_DEMO=true
```

When disabled (default), navigation and single-user research UX are unchanged.

## Surfaces

- `/advisor` — Overview dashboard
- `/advisor/clients` · `/advisor/clients/[id]`
- `/advisor/meetings` · `/advisor/tasks`
- `/advisor/research` · `/advisor/portfolios`

## Architecture

```
Advisor Layer (lib/advisor + components/advisor)
        ↓
Presentation Layer
        ↓
Existing Research Platform (untouched)
```

## Non-goals

Auth · Broker · Trading · Tax · Billing · CRM · Email · Calendar · Multi-user · Client management logic · Compliance workflow changes

## Trust

Advisor layer never mutates research conclusions, evidence, confidence, methodology, or decision traces.
