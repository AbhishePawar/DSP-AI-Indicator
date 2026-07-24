# AI Challenge Mode

**Status:** Mandatory architecture for research conclusions (PR1.0).  
**Implementation of LLM wiring:** deferred to L1.2 / L1.3 (use existing Copilot ports).

---

## Mandate

For every Research Conclusion / Investment Assessment, DSP AI **must** explain:

1. **Reasons supporting** the conclusion  
2. **Reasons against** the conclusion  
3. **Risks**  
4. **Assumptions**  
5. **Unknowns**

One-sided justification is a product defect.

---

## Port

`compliance.ai_governance`:

```text
ChallengeBrief
  conclusion_summary
  reasons_supporting[]
  reasons_against[]
  risks[]
  assumptions[]
  unknowns[]
  evidence_refs[]

ChallengeModePort.build_challenge(context_ref, conclusion_summary)
```

---

## Placement

Analysis IA section **AI Challenge Mode** (after AI Copilot, before Evidence).

---

## Rules

- Runs on **backend** (Copilot / explanation engines) — never in the browser.  
- Must cite evidence refs where available (KG / report citations).  
- Research Mode language for conclusions; no Buy/Sell unless SEBI flags on.  
