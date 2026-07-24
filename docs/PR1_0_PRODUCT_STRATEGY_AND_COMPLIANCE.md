# PR1.0 — Product Strategy & Compliance Architecture

**Status:** Complete (architecture + docs + Research Mode presentation)  
**Package:** `compliance` **0.1.0**  
**Engines / APIs:** Unchanged  

---

## Summary

DSP now operates as a **two-phase platform** in product strategy:

- **Phase 1 Research Mode** (default) — decision support language  
- **Phase 2 SEBI Mode** (flags + ports only) — future official recommendations  

No investment logic, valuation, recommendation engines, workflow, KG, or API
contracts were redesigned.

---

## Deliverables

| Area | Artifact |
|---|---|
| Compliance context | `packages/compliance/` |
| Feature flags | `feature_flags.py` + web `featureFlags.ts` |
| Terminology | `terminology.py` + web `terminology.ts` |
| Metric / IA standards | `metric_presentation`, `analysis_sections`, `MetricCard` |
| Consensus / Challenge ports | `analyst_consensus`, `ai_governance` |
| Docs | Product / Research / SEBI / Compliance / Flags / UX / Consensus / Challenge |

---

## Migration notes

1. UI authors must use `presentAction` / `presentFieldLabel` — never hard-code
   BUY/SELL/HOLD in Research Mode.  
2. Set web env from `apps/web/.env.example` (Phase 1 defaults).  
3. Ops may set `RESEARCH_MODE` etc. for backend-side consumers of
   `load_feature_flags()`.  
4. SEBI Mode remains **off** until registration + explicit flag flip.  
5. Existing recommendation engine enums (`buy`/`sell`/`hold`) are unchanged;
   mapping is presentation-only.  

---

## Regression

Existing business suites remain green; compliance adds additive tests only.
