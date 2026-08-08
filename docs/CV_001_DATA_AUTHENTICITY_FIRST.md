# CV-001 — Data Authenticity First

| Field | Value |
|---|---|
| **ID** | **CV-001** |
| **Status** | **MANDATORY · NON-NEGOTIABLE** |
| **Effective** | 2026-07-28 |
| **Violation class** | **Architecture Violation** |
| **Authority** | [CORE_VALUES.md](CORE_VALUES.md) · [ARCHITECTURE_BIBLE.md](ARCHITECTURE_BIBLE.md) · [ADR-CV-001](adr/ADR-CV-001-data-authenticity-first.md) |

---

## Rule

DSP AI Indicator **SHALL NEVER** display fabricated, placeholder, guessed,
example, dummy, assumed, or manually invented financial or market numbers in
any **production research output**.

**Violation = Architecture Violation.** Architecture review **MUST FAIL**.

---

## Allowed numeric sources

Every displayed number **MUST** belong to **exactly one** category:

| # | Category | Examples |
|---|---|---|
| 1 | **Market Data** | Exchange quotes; approved market-data providers |
| 2 | **Financial Statement Data** | Filings; annual / quarterly reports; audited statements |
| 3 | **DSP AI Calculated** | Deterministic engine output: valuation, MoS, fair value, quality scores |
| 4 | **User Input** | Symbol, holdings, preferences entered by the user |
| 5 | **Derived Metrics** | Formula outputs using **only** authenticated inputs from 1–4 |

Nothing else is permitted.

### Honesty labels vs fabrication

- Trust category **Calculated** / model **Estimated Value** may label
  **DSP AI Calculated** or **Derived** outputs that are real engine results.
- Those labels **never** authorize inventing market prices, market caps,
  statement line items, or placeholder ratios when inputs are missing.

---

## Forbidden

Never display in production research output:

- `₹XXXX`, `XX%`, or similar mask placeholders presented as values  
- Dummy / example / made-up numbers  
- Estimated market price or market cap invented when quote/filing is missing  
- Random ratios or invented valuation outputs  
- Any numeric filler to “complete” a UI  

---

## If data is unavailable

Display:

> **Data unavailable.**

Never fabricate numbers.

---

## Mandatory research report header

Every research report **MUST** display:

| Field |
|---|
| Current Market Price |
| Intrinsic Value |
| Margin of Safety |
| Fair Value Range |
| Expected CAGR (if available — else **Data unavailable.**) |
| Confidence |
| Overall Score |
| Timestamp |
| Research Mode |

Missing header fields use **Data unavailable.** — never invent.

---

## Metric metadata (internal)

Every metric **SHALL** carry:

| Field | Purpose |
|---|---|
| Source | One of the five allowed categories |
| Timestamp | As-of / observation time |
| Reporting period | Filing or calculation period when applicable |
| Calculation engine | Owning engine / package (if calculated/derived) |
| Version | Engine or schema version |
| Confidence | When applicable |

---

## Explainability

Every score **MUST** be traceable to:

- Formula  
- Raw inputs  
- Weights  
- Engine  
- Contribution  

No black-box outputs in production research artifacts.

---

## Enforcement

Future report generators **MUST** validate before emit:

| ✓ | Check |
|---|---|
| | No placeholder values |
| | No fabricated market data |
| | No fabricated financial statement data |
| | Every metric has provenance |
| | Every calculated metric is reproducible |

See [ARCHITECTURE_CHECKLIST.md](ARCHITECTURE_CHECKLIST.md) ·
[CODE_REVIEW_CHECKLIST.md](CODE_REVIEW_CHECKLIST.md) ·
[IMPLEMENTATION_QUALITY_GATE.md](IMPLEMENTATION_QUALITY_GATE.md).

---

## Non-goals of this governance update

- Does **not** change investment engines, scoring math, APIs, or deterministic behaviour  
- Does **not** authorize new data providers without existing architecture process  
