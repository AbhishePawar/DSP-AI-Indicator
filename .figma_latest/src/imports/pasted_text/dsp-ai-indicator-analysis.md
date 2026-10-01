# DSP AI INDICATOR — FINAL TWO-MODE COMPANY ANALYSIS

## 1. CORE PRODUCT STRUCTURE

Redesign `CompanyAnalysis.tsx` around exactly **TWO customer experiences**:

### 1. SIMPLE RESEARCH

A quick, straightforward company research result.

### 2. DSP BUFFETT INDICATOR ANALYSIS

A comprehensive, evidence-driven research experience that:

1. Generates the complete structured DSP Buffett Indicator analysis.
2. Presents the 14-section research result.
3. Allows the customer to ask follow-up questions **about that exact result** through an integrated chat interface.

**There is NO separate third "Chat with DSP" mode.**

Chat is a built-in follow-up capability of the **DSP Buffett Indicator Analysis result**.

---

# 2. CUSTOMER JOURNEY

The initial company-analysis page should present exactly two choices:

```text
┌─────────────────────────────────────────────┐
│                                             │
│        COMPANY ANALYSIS                     │
│                                             │
│   [ Simple Research ]                       │
│                                             │
│   Get a quick research overview.             │
│                                             │
│   [ DSP Buffett Indicator Analysis ]        │
│                                             │
│   Get the complete evidence-driven          │
│   company analysis.                          │
│                                             │
└─────────────────────────────────────────────┘
```

Do not show a separate Chat button at this stage.

---

# 3. OPTION 1 — SIMPLE RESEARCH

The first option is:

## Simple Research

Purpose:

**Give the customer a quick understanding of the company.**

The result can include the appropriate existing DSP research information such as:

* company overview
* key financial metrics
* business overview
* financial trends
* growth
* key strengths
* key risks
* valuation summary
* relevant research information
* sources/evidence

Keep this experience concise.

Do NOT force the customer through the full 14-section Buffett analysis.

The exact calculations and data remain backend-authoritative.

---

# 4. OPTION 2 — DSP BUFFETT INDICATOR ANALYSIS

The second option is the flagship research experience:

## DSP Buffett Indicator Analysis

Supporting description:

> Get a comprehensive, evidence-driven analysis of the company's business quality, financial strength, economic moat, management, earnings, growth, valuation, margin of safety and risks.

When the customer presses this button, start the full analysis.

---

# 5. STAGED ANALYSIS EXPERIENCE

After clicking:

### DSP Buffett Indicator Analysis

show a professional research-progress experience.

Example:

```text
Identifying Company                    ✓

Collecting Financial Evidence          ✓

Analysing Business Quality              ●

Evaluating Economic Moat                ○

Evaluating Management                   ○

Analysing Earnings & Growth             ○

Evaluating Valuation                    ○

Assessing Risks                         ○

Validating Research                     ○

Preparing DSP Research Report           ○
```

Do NOT expose:

* Gemini
* ChatGPT
* AI provider names
* internal prompts
* provider conflicts
* orchestration
* API information
* technical implementation

The customer should see a professional research process, not the backend architecture.

---

# 6. FINAL BUFFETT ANALYSIS RESULT

After analysis completes, display the complete structured research report.

The report contains exactly these major sections:

## 01 — Company Header

## 02 — Business Quality

## 03 — Buffett-Style Assessment

## 04 — Financial Analysis

## 05 — Economic Moat

## 06 — Management & Capital Allocation

## 07 — Earnings Quality

## 08 — Growth Quality

## 09 — Valuation & Intrinsic Value

## 10 — Margin of Safety

## 11 — Key Risks

## 12 — Strengths & Weaknesses

## 13 — Investment Context

## 14 — Evidence & Sources

---

# 7. RESEARCH TABLE OF CONTENTS

Add a clear section navigation/TOC.

Example:

```text
RESEARCH

01 Overview
02 Business Quality
03 Buffett Assessment
04 Financial Analysis
05 Economic Moat
06 Management
07 Earnings
08 Growth
09 Valuation
10 Margin of Safety
11 Risks
12 Strengths & Weaknesses
13 Investment Context
14 Evidence
```

The TOC should allow the customer to jump directly to sections.

Show the currently active section while scrolling.

On mobile, convert it into a compact expandable navigation.

---

# 8. BUSINESS QUALITY

Use the existing DSP Business Quality methodology.

The five domains are:

### Economic Moat — 25%

### Management Quality — 20%

### Financial Strength — 20%

### Earnings Quality — 20%

### Growth Quality — 15%

Do NOT change these weights.

Do NOT recreate the calculation in the frontend.

The frontend displays the backend-authoritative result.

The visualization should include:

* overall Business Quality
* score/rating
* five component results
* concise explanation
* evidence access

---

# 9. BUFFETT-STYLE ASSESSMENT

Create a dedicated:

## Buffett-Style Assessment

Use the existing analytical evidence to organize:

* understandable business
* economic moat
* management quality
* financial strength
* earnings consistency
* debt position
* ROE where available
* cash generation
* valuation
* margin of safety
* long-term risks

Do not create a separate frontend calculation.

If evidence is unavailable:

**Unavailable**

Do not estimate.

---

# 10. FINANCIAL ANALYSIS

Show relevant available financial information:

* revenue
* earnings
* EPS
* margins
* cash flow
* debt
* liquidity
* profitability
* ROE
* ROCE
* historical trends

Use clean visualizations.

Prioritize meaningful trends over raw-data overload.

---

# 11. ECONOMIC MOAT

Create:

## Economic Moat

Show:

* moat assessment
* score where available
* confidence/status
* explanation
* evidence

The customer must be able to understand **why** the assessment was reached.

---

# 12. MANAGEMENT & CAPITAL ALLOCATION

Create:

## Management & Capital Allocation

Show available evidence regarding:

* management quality
* capital allocation
* reinvestment
* dividends
* buybacks
* acquisitions
* debt reduction
* governance-related evidence where supported

Never fabricate unavailable information.

---

# 13. EARNINGS QUALITY

Show:

* revenue trend
* earnings trend
* cash conversion
* margin stability
* earnings consistency
* earnings-quality assessment

Use charts where appropriate.

---

# 14. GROWTH QUALITY

Show:

* revenue growth
* earnings growth
* quality of growth
* cash generation
* margin behaviour
* sustainability indicators

Do not treat growth as automatically positive.

---

# 15. VALUATION & INTRINSIC VALUE

Create a prominent valuation visualization:

### Current Market Price

₹X

### DSP Intrinsic Value

₹Y

### Margin of Safety

Z%

The visual relationship between price and intrinsic value should be immediately understandable.

Do not independently calculate these values in the frontend.

Use the authoritative backend output.

---

# 16. MARGIN OF SAFETY

Make this a major visual element.

Clearly separate:

**Business Quality**

from:

**Valuation**

A high-quality business and an attractive valuation are different analytical questions.

The interface must communicate this distinction.

---

# 17. KEY RISKS

Create:

## Key Risks

Show evidence-supported risks such as:

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

# 18. STRENGTHS & WEAKNESSES

Create a balanced layout:

### Strengths

### Weaknesses

Maintain strong visual symmetry.

Neither side should visually dominate merely for aesthetic effect.

---

# 19. INVESTMENT CONTEXT

Show the existing DSP analytical context:

* Business Quality
* Valuation
* Margin of Safety
* Risk
* Confidence
* existing backend-authoritative status/recommendation

Do not create a new recommendation algorithm in the frontend.

---

# 20. EVIDENCE & SOURCES

Create:

## Evidence & Sources

Important conclusions should be traceable to evidence.

Evidence drawers/cards can show:

* metric
* value
* period
* source
* analytical context
* confidence/status

Keep the main report clean by using progressive disclosure.

---

# 21. THE MOST IMPORTANT FEATURE — FOLLOW-UP CHAT

After the DSP Buffett Indicator Analysis result has been generated, the customer should be able to **chat about the result**.

This is NOT a third product mode.

It is a continuation of the Buffett analysis.

Think of it as:

```text
DSP Buffett Indicator Analysis
          ↓
Complete Research Report
          ↓
Customer has questions
          ↓
Ask DSP
          ↓
Follow-up conversation
```

The customer may ask:

> Why is the Business Quality score this high?

> Why is the moat considered strong?

> What is causing the financial weakness?

> Why is the intrinsic value different from the market price?

> Explain the margin of safety.

> What are the biggest risks?

> Is the earnings growth sustainable?

> Which factor is the biggest weakness?

The conversation must remain anchored to the generated analysis.

---

# 22. CHAT MUST BE CONTEXTUAL

When the customer starts follow-up chat, DSP already knows:

* selected company
* generated analysis
* Business Quality
* Buffett assessment
* financial analysis
* moat assessment
* management assessment
* earnings quality
* growth quality
* valuation
* intrinsic value
* margin of safety
* risks
* evidence

The customer should NOT have to repeat the company name or explain the previous analysis.

---

# 23. FOLLOW-UP CHAT UI

Do not turn the entire research page into a permanent chatbot.

The research report remains the primary interface.

Use an elegant:

### Ask DSP

or:

### Ask about this analysis

entry point.

Possible implementations:

* bottom chat drawer
* side panel
* expandable conversation panel
* floating contextual action

Choose the design that best fits the existing application while preserving report readability.

---

# 24. CONTEXTUAL "ASK DSP" ACTIONS

Relevant sections may include:

### Business Quality

**Ask why this score was assigned**

### Buffett Assessment

**Ask about this assessment**

### Economic Moat

**Ask about the moat**

### Financial Analysis

**Ask about the financials**

### Earnings Quality

**Ask about earnings**

### Growth Quality

**Ask about growth**

### Valuation

**Ask about valuation**

### Margin of Safety

**Ask about the margin of safety**

### Risks

**Ask about the risks**

These actions should automatically open the follow-up chat with the appropriate section context.

---

# 25. CHAT MUST NOT BECOME A SECOND ANALYTICAL ENGINE

The follow-up chat should explain, clarify and explore the existing DSP result.

It must NOT independently create conflicting calculations for:

* Business Quality
* Intrinsic Value
* Margin of Safety
* Economic Moat
* Financial Strength
* Earnings Quality
* Growth Quality
* recommendation

The authoritative DSP analysis remains the source of truth.

---

# 26. CHAT AND REPORT MUST BE CONNECTED

If the customer asks a question about a specific section, the conversation can provide:

**View in Research**

For example:

> The main factor affecting earnings quality is...

**View Earnings Quality**

Clicking this returns to Section 07.

Similarly:

> The valuation assessment is based on...

**View Valuation**

This takes the customer to Section 09.

This creates a seamless:

**Read → Ask → Understand → Return to Research**

loop.

---

# 27. REPORT REMAINS A REPORT

Do NOT turn the 14 sections into chat bubbles.

The structured report must retain:

* charts
* scorecards
* tables
* cards
* evidence drawers
* visual comparisons
* analytical summaries

Chat is layered on top of the report.

---

# 28. NO PERSONAL FINANCIAL HEALTH

Remove the Personal Financial Health Score completely from `CompanyAnalysis.tsx`.

Do NOT show:

* Financial Health Score
* 0–1000 personal health meter
* personal wealth
* personal portfolio health
* personal financial profile

This page is about the selected company.

---

# 29. SIMPLE RESEARCH VS DSP BUFFETT ANALYSIS

Make the difference immediately understandable.

|                   | Simple Research         | DSP Buffett Indicator Analysis      |
| ----------------- | ----------------------- | ----------------------------------- |
| Purpose           | Quick understanding     | Deep company research               |
| Depth             | Concise                 | Comprehensive                       |
| Business Quality  | Summary                 | Detailed                            |
| Buffett Framework | No/full limited         | Full                                |
| Valuation         | Summary                 | Detailed                            |
| Margin of Safety  | Summary where available | Detailed                            |
| Risks             | Key risks               | Comprehensive evidence-backed risks |
| Evidence          | Essential               | Detailed                            |
| Follow-up Chat    | Not required            | **Available after result**          |

Do not make Simple Research feel broken or incomplete.

It is simply the faster research experience.

---

# 30. INITIAL SCREEN

The initial company-analysis screen should contain exactly two primary actions:

### SIMPLE RESEARCH

**Research**

> Get a quick overview of this company.

### DSP BUFFETT INDICATOR ANALYSIS

**Analyze**

> Get the complete DSP Buffett-style company analysis.

There should be NO standalone Chat button.

---

# 31. AFTER SIMPLE RESEARCH

Show the concise research result.

Provide an obvious pathway to the deeper experience:

### Want the complete analysis?

**Run DSP Buffett Indicator Analysis**

This allows users to upgrade from quick research to comprehensive research without leaving the company context.

---

# 32. AFTER BUFFETT ANALYSIS

Show:

### Complete DSP Research Report

with:

**Ask DSP about this analysis**

The customer can continue asking questions without restarting the analysis.

---

# 33. RESPONSIVE DESIGN

Desktop:

* structured research workspace
* section TOC
* strong data visualization
* optional contextual chat panel

Mobile:

* stacked sections
* collapsible TOC
* sticky/accessible Ask DSP control
* expandable evidence
* readable charts
* no horizontal overflow

The chat should open naturally without destroying the report context.

---

# 34. VISUAL DESIGN

Design language:

**Premium + Intelligent + Trustworthy + Evidence-driven**

Avoid:

* crypto aesthetics
* casino/trading aesthetics
* excessive neon
* excessive gradients
* excessive red/green
* generic AI chatbot aesthetics
* visual clutter

Use:

* sophisticated typography
* consistent spacing
* strong visual symmetry
* clean grid
* restrained financial colour system
* professional charts
* clear hierarchy
* premium research-terminal feel

---

# 35. SEARCH ICON

If the existing blue navigation bar currently says:

**Research**

replace the text with a clean **magnifying-glass/search icon**.

It must remain a functional navigation control.

Clicking it should take the customer to the appropriate research/search page.

---

# 36. DO NOT CHANGE THE BACKEND METHODOLOGY

This Figma/UI work must NOT introduce:

* new financial formulas
* new scores
* new valuation calculations
* new weights
* new recommendation logic
* duplicated analytical engines

The frontend presents the authoritative backend result.

---

# 37. FINAL PRODUCT ARCHITECTURE

The complete product experience is:

```text
                 COMPANY
                    │
          ┌─────────┴─────────┐
          │                   │
          ▼                   ▼
   SIMPLE RESEARCH      DSP BUFFETT
                           INDICATOR
                           ANALYSIS
                               │
                               ▼
                    STAGED ANALYSIS
                               │
                               ▼
                    COMPLETE RESEARCH
                         REPORT
                               │
                               ▼
                         ASK DSP
                               │
                               ▼
                      FOLLOW-UP CHAT
                               │
                               ▼
                    QUESTIONS ABOUT
                     THE SAME RESULT
```

There are **ONLY TWO customer choices**:

### 1. Simple Research

### 2. DSP Buffett Indicator Analysis

The chat is **not a third choice**.

It is a built-in follow-up capability available **after the DSP Buffett Indicator Analysis result is generated**.

---

# 38. FINAL UX PRINCIPLE

The product should communicate:

### Simple Research

**"Give me the quick picture."**

### DSP Buffett Indicator Analysis

**"Give me the complete research,**
