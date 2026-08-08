# EPIC-A006 — Policy Architecture

```
Caller-supplied artifacts
  R001 · R002 · R004 · R005 · A002 · A003 · A004 · A005
        ↓
Policy Loader (+ Exception Registry)
        ↓
Rule Registry (deterministic order by rule_id)
        ↓
Rule Evaluator (structural presence / equality only)
        ↓
Compliance Checker
  summary · violations · warnings · audit trail
        ↓
Citations · Provenance · Audit metadata
```

No providers, engines, calculations, valuation, scoring, optimisation, mutation,
or recommendations. Missing artifact for a rule → `"Data unavailable."` / `unavailable`.
