# ADR-CV-001 — Data Authenticity First

| Field | Content |
|---|---|
| **Status** | **Accepted** |
| **Date** | 2026-07-28 |
| **ID** | ADR-CV-001 |
| **Related** | [CV_001_DATA_AUTHENTICITY_FIRST.md](../CV_001_DATA_AUTHENTICITY_FIRST.md) · [CORE_VALUES.md](../CORE_VALUES.md) · [ARCHITECTURE_BIBLE.md](../ARCHITECTURE_BIBLE.md) |

## Context

Production research UIs and reports can be pressured to “fill” missing quotes,
statement lines, or scores with placeholders, examples, or guessed figures.
That destroys institutional trust and violates honesty / thin-client / Research
Mode principles.

## Decision

Adopt **CV-001 Data Authenticity First** as a permanent core architecture value:

1. Every displayed number must be Market Data, Financial Statement Data,
   DSP AI Calculated, User Input, or Derived from authenticated inputs only.  
2. Unavailable data → display **Data unavailable.** — never fabricate.  
3. Research reports must show the mandatory header fields (price, IV, MoS,
   fair-value range, CAGR if available, confidence, overall score, timestamp,
   Research Mode).  
4. Metrics carry provenance metadata; scores are explainable (formula, inputs,
   weights, engine, contribution).  
5. Violation **fails** architecture review and quality gates.

## Consequences

- Future report generators must validate authenticity before emit.  
- Demo/sample modes must not silently present invented numbers as production
  research (explicit non-production labeling if fixtures exist for tests).  
- No engine, scoring, API, or deterministic math changes are required by this
  ADR — governance and review enforcement only.

## Alternatives considered

| Alternative | Why rejected |
|---|---|
| Allow “example” numbers in UI with small disclaimer | Still misleads; fails institutional trust |
| Client-side estimated market price when quote missing | Thin-client + CV-001 forbid invented market data |
| Soft guideline only | Non-negotiable; must fail review |

## India / Research Mode notes

Research Mode default remains; authenticity applies equally in Research and
any future SEBI Mode. SEBI flags do not authorize fabricated numbers.
