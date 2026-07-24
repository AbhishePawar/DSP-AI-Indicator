# Feature Flag Strategy

**Epic:** PR1.0

All recommendation-facing UI **must** respect these flags.

---

## Flag catalog

| Flag | Env (backend / ops) | Env (web) | Phase 1 default |
|---|---|---|---|
| ResearchMode | `RESEARCH_MODE` | `NEXT_PUBLIC_RESEARCH_MODE` | `true` |
| RecommendationMode | `RECOMMENDATION_MODE` | `NEXT_PUBLIC_RECOMMENDATION_MODE` | `false` |
| SEBIMode | `SEBI_MODE` | `NEXT_PUBLIC_SEBI_MODE` | `false` |
| ShowTargetPrice | `SHOW_TARGET_PRICE` | `NEXT_PUBLIC_SHOW_TARGET_PRICE` | `false` |
| ShowBuySell | `SHOW_BUY_SELL` | `NEXT_PUBLIC_SHOW_BUY_SELL` | `false` |
| ShowModelPortfolio | `SHOW_MODEL_PORTFOLIO` | `NEXT_PUBLIC_SHOW_MODEL_PORTFOLIO` | `false` |
| ShowResearchAlerts | `SHOW_RESEARCH_ALERTS` | `NEXT_PUBLIC_SHOW_RESEARCH_ALERTS` | `false` |

---

## Derived gates

| Capability | Requires |
|---|---|
| BUY/SELL/HOLD labels in UI | RecommendationMode ∧ SEBIMode ∧ ShowBuySell |
| Official Target Price label | RecommendationMode ∧ SEBIMode ∧ ShowTargetPrice |
| Research-only posture | ResearchMode ∧ ¬SEBIMode |

Implemented in:

- `compliance.feature_flags.FeatureFlags`  
- `apps/web/src/lib/featureFlags.ts`

---

## Policy

- Flags control **presentation**, not engine math.  
- Inconsistent combos emit soft warnings via `FeatureFlags.validate()`.  
- Never hard-code tip language in components — call `presentAction` /
  `presentFieldLabel`.  

---

## Phase 2 flip (documentation only)

After SEBI registration, ops sets Recommendation + SEBI + Show* flags true.
No backend redesign required.
