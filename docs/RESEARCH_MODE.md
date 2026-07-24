# Research Mode

**Default product mode — Phase 1**

```text
RESEARCH_MODE=true
RECOMMENDATION_MODE=false
SEBI_MODE=false
```

---

## Intent

Provide professional investment research and decision support **without**
issuing formal Buy / Sell / Hold recommendations or official target prices.

---

## Forbidden hard-coded UI words (Research Mode)

Do not display as user-facing labels:

- BUY · SELL · HOLD  
- STRONG BUY · STRONG SELL  
- TARGET PRICE  
- Stock Recommendation (as tip language)

---

## Replacement vocabulary

| Legacy / engine token | Research Mode UI |
|---|---|
| BUY / STRONG BUY | **DSP View → Attractive** |
| SELL / STRONG SELL | **DSP View → Caution** |
| HOLD | **DSP View → Fairly Valued** |
| Target Price | **Estimated Intrinsic Value Range** |
| Recommendation | **Research Conclusion** |
| Stock Recommendation | **Investment Assessment** |

Engines may still emit `buy` / `sell` / `hold` internally.  
**Presentation** maps via `compliance.terminology` / `apps/web` `terminology.ts`.

---

## Disclaimers

Default research disclaimer: `compliance.disclaimer_engine.default_research_disclaimer()`.

Web banner: `ResearchModeBanner`.

---

## Activation of tip-like language

Only when SEBI Mode gates pass — see [SEBI_MODE.md](SEBI_MODE.md) and
[FEATURE_FLAG_STRATEGY.md](FEATURE_FLAG_STRATEGY.md).
