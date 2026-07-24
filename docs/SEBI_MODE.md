# SEBI Mode

**Phase 2 — architecture only. Do not implement in PR1.0.**

---

## Target flags (after SEBI registration)

```text
RESEARCH_MODE=true
RECOMMENDATION_MODE=true
SEBI_MODE=true
SHOW_BUY_SELL=true
SHOW_TARGET_PRICE=true
SHOW_MODEL_PORTFOLIO=true   # when ready
SHOW_RESEARCH_ALERTS=true   # when ready
```

---

## Surfaces enabled only in SEBI Mode

| Capability | Flag gate |
|---|---|
| Buy / Hold / Sell labels | `ShowBuySell` + SEBI + Recommendation |
| Official Target Price | `ShowTargetPrice` + SEBI + Recommendation |
| Time Horizon | SEBI Mode (future UI) |
| Model Portfolio | `ShowModelPortfolio` |
| Research Alerts | `ShowResearchAlerts` |
| Recommendation History | `recommendation_history` port |
| Client Reports | future reporting surface |
| Advisor Dashboard | future role-gated UI |

---

## What does **not** change at activation

- Valuation engine  
- Recommendation engine domain models  
- Workflow / KG / Copilot engines  
- Public API contracts (additive endpoints only if needed later)  
- Decision math  

Activation is **flag + compliance + UI presentation**.

---

## Compliance prerequisites (future)

- Disclosures & methodology published  
- Conflict register populated  
- Audit trail for recommendation issuance  
- Research archive retention policy  
- AI governance / Challenge Mode attached to every conclusion  

Ports live in `packages/compliance/` — implementations deferred.
