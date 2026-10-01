# DSP AI INDICATOR — FINAL FIGMA UI/UX MASTER PROMPT

## 1. PROJECT OBJECTIVE

Design the production-ready frontend UI/UX for **DSP AI Indicator**, an evidence-driven equity research and company-analysis platform.

The frontend must visually represent the analytical system that already exists in the backend.

This is primarily a **UI/UX improvement and information-architecture task**, not a request to redesign the financial methodology.

The backend/deterministic analytical framework remains the source of truth.

The Figma design must make a sophisticated analytical system feel simple, trustworthy, professional and easy to understand for a future client.

Core product philosophy:

**Evidence → Deterministic Analysis → Business Quality → Valuation → Verification → Explainable Research Result**

---

# 2. CRITICAL BOUNDARY: FRONTEND + BACKEND ARE ONE PRODUCT

The Figma design must be aligned with the existing backend analytical architecture.

Do NOT invent new financial calculations.

Do NOT create frontend versions of backend scoring engines.

Do NOT change the existing methodology simply to make the UI easier to design.

The frontend should present backend-authoritative results.

The frontend is responsible for:

* information hierarchy
* visual communication
* interaction
* navigation
* progressive disclosure
* readability
* evidence presentation
* responsive behaviour
* user experience

The backend remains responsible for:

* data
* financial calculations
* analytical scores
* valuation
* intrinsic value
* margin of safety
* business-quality aggregation
* conflict resolution
* recommendation/status
* evidence validation

---

# 3. IMPORTANT: THIS IS STOCK/COMPANY RESEARCH

This result page is for **company and stock research**.

REMOVE the **Personal Financial Health Score** completely from this experience.

Do NOT show:

* personal Financial Health Score
* 0–1000 personal financial-health meter
* personal portfolio health
* personal financial profile
* personal financial planning metrics

Those belong to a separate personal-finance/client-profile experience.

The stock research result must begin with the **company and investment-analysis context**.

---

# 4. PRIMARY USER JOURNEY

The experience should revolve around:

**Search Company → Analyze → Research → Understand → Investigate**

Client flow:

1. Search for a listed company.
2. Select the correct company/security.
3. Press **Analyze**.
4. DSP identifies and processes the company data.
5. Deterministic analytical engines evaluate the company.
6. Business Quality Aggregator combines the analytical domains.
7. Valuation and intrinsic value are presented.
8. Buffett-style analysis organizes the investment characteristics.
9. Research verification occurs internally.
10. Client receives ONE final research result.

Do not expose internal AI providers or internal orchestration.

---

# 5. DO NOT EXPOSE AI IMPLEMENTATION

The client should NOT see:

* Gemini
* ChatGPT
* AI provider names
* model comparison
* provider disagreement
* internal prompts
* system prompts
* chain-of-thought
* internal orchestration
* hidden research instructions
* provider-specific scores
* technical API information

The client receives one clean, validated research result.

AI is a supporting research/verification layer.

It is NOT presented as the source of financial truth.

---

# 6. RESULT PAGE — MASTER INFORMATION ARCHITECTURE

The final stock-analysis page should follow this hierarchy:

### 01 — Company Header

### 02 — Business Quality

### 03 — Buffett-Style Assessment

### 04 — Financial Analysis

### 05 — Economic Moat

### 06 — Management & Capital Allocation

### 07 — Earnings Quality

### 08 — Growth Quality

### 09 — Valuation & Intrinsic Value

### 10 — Margin of Safety

### 11 — Key Risks

### 12 — Strengths & Weaknesses

### 13 — Investment Context

### 14 — Evidence & Sources

There should be NO separate:

**Personal Financial Health Score**

and NO separate:

**AI Explanation**

section.

AI-generated synthesis should be integrated naturally into the relevant research sections.

---

# 7. COMPANY HEADER

The top of the page should immediately establish:

* company name
* company logo where available
* NSE/BSE/security identity where available
* current market price
* analysis date/time
* relevant market information
* change-company/search action

The header should feel like a professional equity-research terminal rather than a trading app.

---

# 8. BUSINESS QUALITY — PRIMARY COMPANY QUALITY VIEW

Create a prominent:

## Business Quality

This is the core company-quality assessment.

The existing DSP Business Quality Aggregator uses five analytical domains:

### Economic Moat — 25%

### Management Quality — 20%

### Financial Strength — 20%

### Earnings Quality — 20%

### Growth Quality — 15%

These weights are backend methodology.

Do NOT modify them in Figma.

Do NOT create a second frontend calculation.

The UI should visually communicate that Business Quality is a composite analytical result.

---

# 9. BUSINESS QUALITY VISUAL

Create a strong overall Business Quality result.

Show:

* overall score
* rating
* confidence/status
* concise evidence-backed summary

Below it, display five component cards:

### Economic Moat

25%

### Management Quality

20%

### Financial Strength

20%

### Earnings Quality

20%

### Growth Quality

15%

Each component should provide:

* score/rating where available
* short explanation
* status
* evidence interaction

The overall score must have visual priority over the individual components.

---

# 10. BUSINESS QUALITY CONFLICT CHECK

The backend contains deterministic cross-domain conflict resolution.

It can identify situations such as:

* strong moat + weak balance sheet
* excellent management + weak earnings quality
* strong growth + poor cash generation
* high profitability + weak capital allocation
* strong financial strength + weak liquidity
* strong growth + unstable margins

The frontend must NOT expose programming constants or technical penalty rules.

Instead show a human-readable:

## Quality Check

Example:

> Strong growth is accompanied by weaker cash conversion, reducing the durability assessment.

If no significant conflict exists:

> No major cross-factor quality conflict identified.

This makes the analysis transparent without exposing backend implementation.

---

# 11. BUFFETT-STYLE ASSESSMENT

Create a major section:

# Buffett-Style Assessment

This is a **company-level Buffett-inspired investment framework**.

Important distinction:

This is NOT the classic market-level Buffett Indicator.

The company-level framework evaluates:

1. Circle of Competence
2. Economic Moat
3. Management Quality
4. Financial Fortress
5. Earnings Predictability
6. Capital Allocation
7. Intrinsic Value
8. Margin of Safety
9. Long-Term Risks

The purpose is to organize the existing DSP analytical outputs into a Buffett-style research framework.

Do NOT create an independent frontend Buffett calculation.

---

# 12. BUFFETT SCORECARD

Create a highly readable scorecard:

| Buffett Dimension       | DSP Result           |
| ----------------------- | -------------------- |
| Understandable Business | Result               |
| Durable Economic Moat   | Result               |
| Management Quality      | Result               |
| Financial Strength      | Result               |
| Earnings Consistency    | Result               |
| Debt Position           | Result               |
| ROE                     | Result / Unavailable |
| Cash Generation         | Result               |
| Valuation               | Result               |
| Margin of Safety        | Result               |

Important:

Never invent missing metrics.

If reliable backend evidence is unavailable:

**Unavailable**

must be displayed.

Do NOT replace missing information with an AI estimate.

---

# 13. BUFFETT DECISION MATRIX

Create a visual decision matrix that answers:

### Does the company demonstrate the characteristics being evaluated?

Use clear states such as:

* Strong
* Adequate
* Weak
* Unavailable

where supported by backend results.

Avoid excessive green/red visual language.

The design should communicate analysis rather than create an emotional buy/sell interface.

---

# 14. CIRCLE OF COMPETENCE

Create:

## Circle of Competence

Show:

* business understanding
* complexity where available
* supporting evidence
* confidence/status

The purpose is to answer:

> How understandable is this business from the available evidence?

Do not invent qualitative business characteristics when the backend does not have evidence.

---

# 15. ECONOMIC MOAT

Create:

## Economic Moat

Show:

* moat assessment
* score where available
* confidence
* concise explanation
* supporting evidence

Example hierarchy:

**Moat Strength**

Strong

Then:

**Why**

Concise evidence-backed explanation.

Then:

**View Evidence**

---

# 16. MANAGEMENT & CAPITAL ALLOCATION

Create:

## Management Quality

Show:

* management assessment
* capital allocation
* available governance evidence
* confidence
* supporting evidence

Then:

## Capital Allocation

Where available, show:

* reinvestment
* dividends
* buybacks
* acquisitions
* debt reduction
* capital allocation quality

If a field is not supported by reliable evidence:

**Unavailable**

Do not fabricate management actions.

---

# 17. FINANCIAL ANALYSIS

Create a dedicated:

## Financial Analysis

This should provide the core financial picture.

Where available:

* revenue
* profit
* EPS
* margins
* cash flow
* debt
* liquidity
* profitability
* ROE
* ROCE
* other relevant financial metrics

Use clean charts and metric cards.

Do not overload the first viewport.

Prioritize trend and interpretation over raw data density.

---

# 18. FINANCIAL STRENGTH

Create:

## Financial Strength

Visualize:

* balance sheet
* debt
* liquidity
* cash generation
* profitability stability
* overall financial strength

Use actual values where available.

Never fabricate a financial metric.

If unavailable:

**Unavailable**

---

# 19. EARNINGS QUALITY

Create:

## Earnings Quality

Show:

* revenue trend
* earnings trend
* cash conversion
* margin stability
* earnings consistency
* earnings-quality assessment

Use historical trend charts where data is available.

The section should answer:

> Are reported earnings durable and supported by the underlying business?

---

# 20. GROWTH QUALITY

Create:

## Growth Quality

Show:

* revenue growth
* earnings growth
* quality of growth
* cash generation
* margin behaviour
* sustainability indicators

Do not treat growth alone as automatically positive.

Growth should be understood together with:

* cash generation
* margins
* financial strength
* capital allocation

---

# 21. VALUATION

Create a major:

## Valuation

The most important visual relationship is:

**Current Market Price**

vs.

**DSP Intrinsic Value**

Then:

**Margin of Safety**

The frontend must display the backend-authoritative valuation.

Do NOT create a second valuation model in the frontend.

---

# 22. INTRINSIC VALUE

Create a strong visual component:

### Current Market Price

₹X

### DSP Intrinsic Value

₹Y

### Margin of Safety

Z%

Also show:

* valuation methodology
* valuation confidence
* concise explanation
* supporting evidence

The client should understand the relationship visually before reading detailed text.

---

# 23. MARGIN OF SAFETY

Make Margin of Safety visually prominent.

The client should understand:

**Business Quality ≠ Valuation**

A high-quality business can still have an unattractive valuation.

Therefore keep:

**Business Quality**

and

**Valuation / Margin of Safety**

visually distinct.

This is a fundamental part of the research experience.

---

# 24. KEY RISKS

Create:

## Key Risks

Show only evidence-supported risks.

Potential categories:

* financial risk
* leverage
* liquidity
* earnings risk
* margin risk
* competitive risk
* valuation risk
* regulatory risk
* concentration
* cyclicality

Each risk should communicate:

**Risk → Evidence → Potential implication**

Avoid generic AI-generated risk lists.

---

# 25. STRENGTHS & WEAKNESSES

Create two balanced panels:

## Key Strengths

and

## Key Weaknesses

Maintain strong visual symmetry.

Each item should be concise and traceable to analytical evidence.

Do not allow strengths to visually overwhelm weaknesses or vice versa.

The purpose is balanced research communication.

---

# 26. INVESTMENT CONTEXT

Create:

## Investment Context

Present the existing DSP analytical context using:

* Business Quality
* Valuation
* Margin of Safety
* Risk
* Confidence
* existing backend recommendation/status

Do NOT create a separate recommendation algorithm in the frontend.

The frontend is only presenting the authoritative result.

Avoid overly aggressive BUY/SELL styling.

This is a research product, not a trading terminal.

---

# 27. EVIDENCE & SOURCES

Create a dedicated expandable:

## Evidence & Sources

Every important conclusion should be traceable.

Evidence cards/drawers may contain:

* metric
* value
* period
* source
* analytical stage
* confidence/status

The default page should remain clean.

Advanced users should be able to expand the evidence trail.

This is a core differentiator of DSP.

---

# 28. DATA AVAILABILITY STATES

Design clear states for:

### Available

Normal result.

### Partial

Some relevant information exists but analysis is incomplete.

### Unavailable

Reliable information is not available.

### Insufficient Data

There is not enough evidence for a meaningful conclusion.

### Validation Issue

The result could not be sufficiently validated.

Do not replace missing data with AI-generated assumptions.

---

# 29. ANALYSIS LOADING EXPERIENCE

When the client presses Analyze, use a professional research-progress experience rather than a generic spinner.

Example:

**Identifying company**

✓

**Collecting financial evidence**

✓

**Analysing business quality**

●

**Evaluating valuation**

○

**Validating research**

○

**Preparing report**

○

Do not mention AI providers.

Use client-understandable research stages.

---

# 30. ERROR EXPERIENCE

Never expose:

* stack traces
* API URLs
* provider errors
* internal exception names
* developer terminology

Instead:

> We could not complete the analysis with sufficient validated data. Please try again.

If partial results are safe:

> Some sections could not be validated and are marked Unavailable.

---

# 31. DESIGN LANGUAGE

The product should communicate:

**Trust + Intelligence + Financial Discipline + Modern Technology**

Avoid:

* casino/trading
