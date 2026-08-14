# User Trust Standard

**Status:** MANDATORY  
**Product:** Explainable AI Investment Research Platform  
**Primary product feature:** Trust

Every visible insight, recommendation, explanation, metric, chart, AI response,
and dashboard element must satisfy the principles below.

---

## 1. TRACEABLE

Every insight must identify its **source**.

| Source category | Examples |
|---|---|
| Financial Statements | Reported revenue, debt from filings |
| Calculated Metric | Ratios derived by backend engines |
| Valuation Engine | Intrinsic value range from valuation package |
| AI Interpretation | Copilot / Challenge narratives |
| External Market Consensus | Street targets / ratings (when providers exist) |
| User Input | Symbol, date range, preferences |

**Never** present conclusions without indicating origin.

UI pattern: source chip / “Source: …” line on cards, charts, and AI blocks.

---

## 2. EXPLAINABLE

Every conclusion must answer:

1. What happened?  
2. Why did it happen?  
3. Why does it matter?  
4. What should the investor investigate next?

No unexplained metrics, scores, or charts.  
Aligns with Metric Library + Four Question Rule (PR1.1).

---

## 3. CONSISTENT

Identical inputs → identical outputs (deterministic presentation of API envelopes).

Maintain consistency in:

- Terminology (Research Mode maps)  
- Rating system  
- Colors (VLIS semantic tokens)  
- Ordering (PXB analysis order)  
- Metric interpretation  
- Decision logic (**server-side**; UI must not re-decide)  
- Visual language & interaction behaviour (PR1.2)  

---

## 4. ACTIONABLE

Every section must guide **what to investigate next**.

Examples: Review debt trend · Compare with peers · Review cash flow ·
Read annual report · Understand valuation assumptions.

Never leave a section without a next-step affordance (takeaway, Copilot prompt,
or deep link).

---

## 5. HONEST

Never imply certainty where uncertainty exists.

Every displayed value must declare its **epistemic category**:

| Category | Meaning |
|---|---|
| Verified Fact | Reported / audited-style input as provided by data layer |
| Calculated Value | Deterministic backend calculation |
| Estimated Value | Model estimate / range |
| AI Interpretation | Model-generated explanation |
| External Consensus | Third-party aggregate |
| User Input | Entered by user |
| Unknown | Not classified |
| Unavailable | Expected but missing |

Missing data must **never** be hidden.  
Never fabricate values, analyst opinions, or forecasts.

### CV-001 — Data Authenticity First (mandatory)

Production research output **MUST NOT** show fabricated, placeholder, guessed,
example, dummy, or invented financial/market numbers. Display
**Data unavailable.** instead.

Allowed numeric sources only: Market Data · Financial Statement Data ·
DSP AI Calculated · User Input · Derived (authenticated inputs only).

Honesty category **Estimated Value** applies only to real deterministic /
model outputs from authenticated inputs — never to inventing a missing market
price, market cap, or statement line.

Full rule → [CV_001_DATA_AUTHENTICITY_FIRST.md](CV_001_DATA_AUTHENTICITY_FIRST.md) ·
[CORE_VALUES.md](CORE_VALUES.md).

Violation = **Architecture Violation**.

Tier-0 companions → [CV_002_TO_010_TIER0_CORE_VALUES.md](CV_002_TO_010_TIER0_CORE_VALUES.md)
(**CV-002** source-before-score · **CV-005** prefer Unable to calculate ·
**CV-003** explainability · **CV-004** determinism).

---

## 6. TRANSPARENT AI

AI interpretations are **not** financial facts.

Whenever AI generates a conclusion, the UI must keep visible the distinction:

- Raw Financial Data  
- Calculated Metrics  
- AI Interpretation  
- External Analyst Opinion  

Do not blend AI prose into fact rows without labeling.

---

## 7. RESEARCH FIRST

DSP exists to improve investment **understanding**.  
It does **not** exist to encourage trading.

Every screen should educate before any recommendation-like surface.  
Research Mode terminology and flags remain in force until SEBI gates unlock.

---

## Source / category UI checklist

- [ ] Source visible on insight  
- [ ] Category badge/label on values  
- [ ] AI blocks labeled as interpretation  
- [ ] Empty/Unavailable explicit  
- [ ] Next investigation step present  
