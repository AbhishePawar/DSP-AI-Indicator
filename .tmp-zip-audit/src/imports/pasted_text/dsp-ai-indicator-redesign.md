# DSP-AI-INDICATOR — FULL PRODUCT UX/UI RE-AUDIT & PREMIUM REDESIGN

## ROLE

Act as a **Principal Product Designer, UX Architect, Design-System Lead, and Senior Fintech Product Designer with 10+ years of experience** designing premium financial products, investment platforms, analytical dashboards, AI products, and data-heavy SaaS applications.

You are not being asked to simply make the interface prettier.

Your responsibility is to **re-audit the entire DSP-AI-Indicator product structure and improve the information architecture, user journey, visual hierarchy, interaction model, responsive behavior, accessibility, visual consistency, and perceived product quality.**

Think like a designer who has shipped products comparable in quality to:

* premium fintech platforms
* modern investment research terminals
* high-quality SaaS analytics products
* AI-native research applications
* modern consumer financial products

Use **editorial information hierarchy + fintech precision + AI-native interaction design + modern SaaS simplicity**.

The final product should feel:

**Premium · Trustworthy · Intelligent · Calm · Modern · Fast · Simple · Sophisticated · Human**

Do NOT make it look like a generic admin dashboard.

---

# 1. UNDERSTAND THE PRODUCT BEFORE REDESIGNING

DSP-AI-Indicator is an investment research and financial-analysis platform.

The primary audience includes:

* long-term investors
* small and emerging investors
* financially curious users
* users who want institutional-quality analysis without institutional-level complexity

The product should therefore hide unnecessary technical complexity.

The user should feel:

> “I can understand this company without being a financial expert.”

NOT:

> “I need to learn how this dashboard works before I can use it.”

---

# 2. CRITICAL EXISTING PRODUCT CONSTRAINTS

Before changing anything, inspect the existing implementation and preserve functional architecture.

The canonical company analysis route is:

`/analysis`

The current architecture uses:

* `CompanyAnalysisWorkspace`
* `CompanyHeaderBar`
* `WorkspaceLeftNav`
* analysis sections
* lazy-loaded deep-dive sections
* context panel
* research/export functionality
* AI Copilot functionality

The `/analysis` page is the canonical analysis experience.

DO NOT create a competing analysis architecture.

DO NOT create a second dashboard.

DO NOT duplicate the existing analysis system.

DO NOT create parallel navigation systems.

DO NOT alter backend algorithms, API contracts, research logic, AI Gateway logic, deterministic DSP pipeline, or data-source architecture as part of this UI/UX redesign.

The redesign is primarily a **product experience and frontend presentation exercise**.

---

# 3. PROTECTED LANDING PAGE

The existing landing/first page is already approved and must remain functionally and visually protected.

DO NOT redesign the landing page from scratch.

DO NOT replace its existing search-first experience.

DO NOT modify its backend behavior.

DO NOT modify its API contract.

DO NOT remove existing landing-page functionality.

Only make changes if they are absolutely required for visual consistency with the broader design system, and preserve the existing approved experience.

---

# 4. PRIMARY PRODUCT FLOW

The product should have a very clear mental model:

## STEP 1 — Discover

User searches for a company.

## STEP 2 — Choose analysis

The user should clearly understand that there are **two primary analysis paths only**:

### 1. Simple Research

A straightforward company research experience.

### 2. DSP Buffett Indicator Analysis

A deeper structured investment analysis experience.

Do NOT introduce a third competing primary analysis mode.

Do NOT overload the user with technical engine names.

---

# 5. ANALYSIS EXPERIENCE

The DSP Buffett Indicator Analysis experience should be treated as the flagship product experience.

The user should receive:

1. Company identity
2. Key market information
3. High-level result
4. Structured Buffett-style analysis
5. Visual financial evidence
6. Important risks
7. Supporting evidence/sources
8. Ability to ask follow-up questions

The user should NOT see internal AI orchestration.

Do NOT expose:

* Gemini vs OpenAI
* provider disagreement
* internal prompts
* research orchestration
* model selection
* hidden verification workflows
* backend pipeline terminology
* internal confidence calculations unless explicitly intended as user-facing evidence

The interface should communicate the **result**, not the machinery.

---

# 6. MAJOR UX PROBLEM TO SOLVE

The current architecture contains a very large number of sections.

Existing architecture includes areas such as:

* Executive Summary
* Valuation
* Business Quality
* Management
* Economic Moat
* Risk
* Financial Performance
* AI Committee
* Ownership
* Peers
* AI Copilot
* Documents
* News
* Settings
* Downloads
* Explainability
* Evidence
* Timeline
* Ratings
* Valuation Transparency
* Research
* Buffett
* Compliance

This is powerful internally, but potentially overwhelming to a normal investor.

Therefore redesign the **information hierarchy**, not the underlying functionality.

Use:

### Progressive disclosure

Show the most important information first.

Hide secondary information until requested.

Use:

* primary sections
* secondary deep dives
* expandable cards
* “View details”
* “See evidence”
* “Ask about this”
* contextual drawers
* modal/detail views where appropriate

Avoid putting every possible section into the user's face simultaneously.

---

# 7. RECOMMENDED INFORMATION ARCHITECTURE

Explore a cleaner hierarchy such as:

## PRIMARY

### Overview

The most important information.

### Buffett Analysis

The flagship structured analysis.

### Financials

Financial performance and trends.

### Valuation

Intrinsic value and valuation evidence.

### Business

Business quality + moat.

### Risk

Financial and business risks.

## SECONDARY / DEEP DIVE

Move less frequently used functionality into:

**Deep Dive**

Containing:

* Management
* Ownership
* Peers
* Evidence
* Timeline
* Documents
* News
* Explainability
* Valuation Transparency
* Compliance
* Research

## TOOLS

Separate utility actions from analytical navigation:

* AI Follow-up
* Export
* Settings

Do not necessarily implement this exact structure blindly.

First audit the current implementation and determine the cleanest hierarchy.

The principle is:

> **Prioritize understanding over feature discovery.**

---

# 8. HEADER REDESIGN

Audit the company header extremely carefully.

The header should establish immediate context:

**Company name**
Ticker
Exchange
Current price
Daily change
Market cap
Important compact metrics

Avoid making the header look like a dense trading terminal.

Use:

* strong typography
* meaningful grouping
* restrained badges
* consistent metric spacing
* subtle dividers
* compact secondary information

Create clear hierarchy between:

### Identity

Company + ticker

### Market snapshot

Price + daily change

### Key metrics

Market cap / 52W / ROE etc.

Do not make every metric visually equal.

---

# 9. NAVIGATION REDESIGN

Audit the left navigation.

The navigation should answer:

> “Where am I?”

and

> “What can I learn next?”

It should NOT become a catalogue of every backend capability.

Use strong grouping.

Example:

**ANALYSIS**

Overview
Buffett Analysis
Financials
Valuation
Business
Risk

**DEEP DIVE**

Management
Peers
Ownership
Evidence
Documents
News

**TOOLS**

AI Follow-up
Export
Settings

Use visual hierarchy rather than dozens of equally weighted items.

---

# 10. VISUAL HIERARCHY

Establish a strict hierarchy:

### Level 1

Company + primary conclusion

### Level 2

Major analytical categories

### Level 3

Metrics

### Level 4

Supporting evidence

### Level 5

Technical/source metadata

Users should understand the page by scanning for approximately 5–10 seconds.

If everything looks important, nothing looks important.

---

# 11. RESULT PAGE DESIGN

The result page should feel like a **premium research report that happens to be interactive**.

Not a spreadsheet.

Not a developer dashboard.

Not a generic AI chatbot.

Not a trading terminal.

Use:

* generous whitespace
* strong alignment
* editorial typography
* structured cards
* clean charts
* subtle borders
* restrained elevation
* consistent corner radii
* predictable spacing

Avoid:

* excessive gradients
* excessive glassmorphism
* excessive shadows
* excessive pills
* oversized cards
* decorative elements without meaning

---

# 12. RESULT SUMMARY

The first viewport of the analysis should answer:

### What is this company?

### What does the analysis say?

### Why?

### What should I investigate next?

The first screen should not require scrolling through ten sections before the user understands the result.

Create a visually dominant:

**Investment Analysis Summary**

with:

* concise thesis
* important positives
* important concerns
* valuation context
* key financial trend
* risk context
* source/evidence affordance

Keep the content concise.

Use progressive disclosure for deeper explanations.

---

# 13. VISUAL DATA PRESENTATION

Financial information should be visual wherever visual representation improves comprehension.

Prefer:

* line charts
* bar charts
* compact trend cards
* comparison visuals
* valuation ranges
* historical trend indicators
* margin/ROE trend visualizations
* earnings-growth visualizations
* debt/cash visualizations

Do not turn every number into a chart.

Use charts only when they improve understanding.

Every chart should have:

* clear title
* period
* units
* source
* concise interpretation

---

# 14. CHART DESIGN LANGUAGE

Create one unified chart language.

Standardize:

* axis typography
* labels
* grid lines
* tooltip design
* positive/negative semantics
* historical vs current values
* source placement
* empty states
* unavailable states

Charts should feel like one product rather than being independently designed.

---

# 15. BUFFETT ANALYSIS EXPERIENCE

The DSP Buffett Indicator Analysis should feel like a **guided investment reasoning experience**.

Avoid presenting a huge wall of metrics.

Structure the experience into understandable concepts:

### Business

What does the company do?

### Quality

How strong is the underlying business?

### Moat

What protects the business?

### Management

How is capital being managed?

### Financial Strength

How strong are the financials?

### Valuation

What does the valuation imply?

### Risk

What can go wrong?

### Overall Evidence

What supports the analysis?

Each section should have:

**Conclusion → Evidence → Visual → Details**

This is much easier to consume than:

**Metric → Metric → Metric → Metric**

---

# 16. INTERACTIVE EXPLANATION MODEL

Every important conclusion should support:

**“Why?”**

For example:

> Strong Financial Quality

Then:

**Why?**

Clicking should reveal:

* supporting metrics
* historical trend
* source
* short explanation

Do not force the user to navigate to another page just to understand a conclusion.

---

# 17. CHAT / FOLLOW-UP EXPERIENCE

The Buffett analysis should support conversational follow-up.

The user should be able to ask questions about the result.

The chat should feel like:

> “Ask about this analysis”

rather than a generic ChatGPT clone.

Use contextual prompts such as:

* Why is valuation considered expensive?
* What is the biggest risk?
* Explain the moat simply.
* What changed in the last 5 years?
* Which financial metric worries you most?
* Explain this result like I'm a beginner.

The AI conversation must remain contextually attached to the company analysis.

---

# 18. CHAT UI

Do NOT let the chat dominate the analysis page.

The analysis remains primary.

Chat should appear through:

* contextual “Ask about this”
* follow-up drawer
* expandable conversation panel
* fixed composer when active

When chat is inactive, preserve maximum analysis space.

When chat opens, maintain clear visual separation between:

**Research result**

and

**Conversation**

---

# 19. SOURCE / TRUST DESIGN

Trust is critical for a financial product.

Create a consistent source treatment.

Every important data block should be able to communicate:

* source
* reporting period
* data status
* unavailable state

Use subtle source badges rather than giant citations.

Examples:

`Source: Screener.in`

`Source: NSE`

`FY2026`

`Data unavailable`

Do not fabricate information.

Do not visually imply certainty where data is unavailable.

---

# 20. EMPTY STATES

Audit every empty state.

Avoid:

> No data.

Instead explain:

**Data unavailable**

Short explanation:

> This information is not currently available from connected data sources.

Use useful next actions where appropriate.

Never create fake financial data just to fill empty space.

---

# 21. LOADING STATES

Loading should feel premium and calm.

Use:

**Preparing your analysis…**

with lightweight skeletons where useful.

Avoid exposing backend processing details.

Do NOT show:

* AI model names
* provider verification
* internal research steps
* technical pipeline stages

The user should feel that the system is simply preparing their result.

---

# 22. ERROR STATES

Errors should be human-readable.

Avoid raw:

* API errors
* stack traces
* HTTP status codes
* JSON errors
* provider failures

Use:

**We couldn't complete this section**

Then:

**Try again**

or

**Continue with available analysis**

The interface should preserve already available results wherever possible.

---

# 23. RESPONSIVE DESIGN

Do not treat mobile as a shrunken desktop.

Design explicitly for:

### Desktop

Full workspace.

### Tablet

Collapsed navigation + optimized content width.

### Mobile

Drawer navigation + single-column analysis + bottom/floating contextual actions.

Charts must remain readable.

Cards must not become tiny.

Horizontal scrolling should be minimized.

---

# 24. VISUAL SYMMETRY

Apply strong visual symmetry throughout the product.

Audit:

* left/right margins
* card widths
* section spacing
* chart alignment
* heading alignment
* metric alignment
* sidebar/content proportions
* button alignment
* icon alignment
* vertical rhythm

The page should feel deliberately composed.

No accidental gaps.

No uneven card heights where unnecessary.

No arbitrary alignment changes between sections.

---

# 25. DESIGN SYSTEM

Create or refine a unified design system.

Define:

### Typography

* Display
* H1
* H2
* H3
* Body
* Caption
* Numeric/financial data

### Spacing

Use a consistent spacing scale.

### Radius

Use a small controlled set.

### Borders

Standardize border opacity and weight.

### Shadows

Use minimal elevation.

### Colors

Define semantic tokens:

* background
* surface
* elevated surface
* primary text
* secondary text
* muted text
* border
* accent
* positive
* negative
* warning
* information

Do NOT use arbitrary colors per component.

---

# 26. FINTECH COLOR LANGUAGE

The interface should feel financially trustworthy without becoming visually boring.

Use a restrained premium palette.

Avoid overusing:

* neon colors
* excessive gradients
* saturated backgrounds
* dark-heavy terminal styling

Important:

The product should feel **premium and modern**, not “crypto dashboard.”

---

# 27. ICONOGRAPHY

Audit all icons.

Use one consistent icon family.

Icons should communicate meaning, not decorate empty space.

Replace unnecessary text labels where a universally understandable icon is stronger.

However:

Do NOT replace important navigation labels with icons alone.

For the research/search action, use a **magnifying-glass/search icon** rather than unnecessarily displaying the word “Research” inside a decorative blue bar.

---

# 28. INTERACTION DESIGN

Audit every interactive element.

Buttons should have:

* clear default state
* hover state
* active state
* disabled state
* loading state
* keyboard focus state

Interactive cards should clearly communicate clickability.

Do not make decorative cards look clickable.

Do not create buttons that exist only for visual decoration.

Every interaction should have a purpose.

---

# 29. MICRO-INTERACTIONS

Use subtle motion for:

* section transitions
* expanding cards
* chart reveal
* navigation selection
* drawer opening
* chat activation
* loading
* hover feedback

Motion should be:

**fast · subtle · purposeful**

Avoid animation for animation's sake.

---

# 30. ACCESSIBILITY

Audit for:

* keyboard navigation
* visible focus
* semantic buttons
* accessible labels
* contrast
* readable font sizes
* chart interpretation
* non-color-only status communication
* reduced-motion support

The interface should remain understandable without relying entirely on color.

---

# 31. INFORMATION DENSITY

This is one of the most important audits.

For every screen ask:

> Does the user need this information right now?

If not:

* collapse it
* move it deeper
* summarize it
* make it contextual

Optimize for **cognitive load**, not information volume.

---

# 32. REMOVE VISUAL NOISE

Identify and reduce:

* duplicate headings
* repeated company names
* redundant labels
* excessive badges
* unnecessary separators
* repeated metadata
* oversized empty containers
* excessive card nesting
* competing primary buttons

Aim for:

**fewer elements, stronger hierarchy.**

---

# 33. CONTEXTUAL ACTIONS

Instead of presenting many permanent actions, surface actions when relevant.

Examples:

Inside valuation:

**Ask why valuation is high**

Inside risk:

**Explain this risk**

Inside financials:

**Show 5-year trend**

Inside moat:

**Explain the moat**

Inside summary:

**Ask about this analysis**

This creates an AI-native experience without turning the whole website into a chatbot.

---

# 34. USER JOURNEY AUDIT

Audit these journeys individually:

### Journey A

Landing → company search → analysis

### Journey B

Landing → simple research

### Journey C

Landing → Buffett analysis

### Journey D

Analysis → understand result

### Journey E

Analysis → inspect evidence

### Journey F

Analysis → ask follow-up question

### Journey G

Analysis → move to another company

### Journey H

Analysis → export/share result

For every journey identify:

* unnecessary clicks
* confusing terminology
* dead ends
* redundant screens
* excessive scrolling
* unclear next action
* inconsistent UI

---

# 35. NAVIGATION BETWEEN COMPANIES

The user should be able to move from one company to another without losing the overall product context.

Maintain:

* search access
* recent companies
* pinned companies where supported
* clear company identity
* predictable back/navigation behavior

Do not make the user restart the product journey unnecessarily.

---

# 36. PERFORMANCE PERCEPTION

Even when the underlying analysis is computationally expensive, the UI should feel fast.

Use:

* skeleton loading
* progressive rendering
* lazy sections
* stable layout dimensions
* optimistic interaction where appropriate
* no layout jumps

The existing architecture already uses lazy-loaded sections; preserve that principle and improve its visual presentation rather than unnecessarily rendering everything at once.

---

# 37. DESKTOP CANVAS

Audit the ideal desktop width.

Avoid:

* excessively wide text blocks
* stretched cards
* giant empty margins
* tiny content centered inside huge canvases

Create a deliberate relationship between:

**navigation → analysis canvas → contextual tools**

The content should remain readable at large monitor widths.

---

# 38. MOBILE EXPERIENCE

Create explicit mobile compositions for:

* landing/search
* company header
* analysis summary
* Buffett analysis
* charts
* deep-dive navigation
* AI follow-up
* sources
* export

Do not simply stack desktop components.

---

# 39. DESIGN FOR BEGINNERS WITHOUT DUMBING DOWN THE PRODUCT

This is critical.

A sophisticated metric can have:

### Technical label

ROE

### Human explanation

Return generated on shareholder capital

### Context

Higher than its historical average

This allows beginners to understand the product while experienced investors can still access the technical information.

Use progressive explanation rather than removing useful data.

---

# 40. CONTENT HIERARCHY

For every analytical card use this structure where appropriate:

### 1. Conclusion

What does this mean?

### 2. Evidence

What supports it?

### 3. Context

Compared with what?

### 4. Detail

How was it derived?

### 5. Source

Where did the information come from?

This creates a trustworthy research experience.

---

# 41. AUDIT ALL CARDS

For every card ask:

* Is the title meaningful?
* Is the most important number visually dominant?
* Is the interpretation obvious?
* Is the source accessible?
* Is the card too tall?
* Is there unnecessary decoration?
* Does it need to be clickable?
* Does it need a chart?
* Can it be merged with another card?

Do not preserve cards merely because they already exist.

---

# 42. AUDIT ALL SECTIONS

For each section determine:

### Keep prominent

Essential to the investor's decision process.

### Keep but simplify

Useful but currently too dense.

### Move to Deep Dive

Useful for advanced users.

### Convert to contextual interaction

Better presented when relevant.

### Remove from primary navigation

Not necessary for the main journey.

Do not delete functionality without understanding dependencies.

This is an IA optimization exercise, not a blind deletion exercise.

---

# 43. NO DUPLICATE INFORMATION

If the same metric appears in:

* header
* summary
* financials
* valuation
* Buffett analysis

determine whether repetition is useful.

Allow intentional repetition only when it serves a different context.

Avoid accidental duplication.

---

# 44. DESIGN FOR TRUST

Financial software must not feel promotional.

Avoid:

* exaggerated success language
* artificial confidence
* flashy “BUY NOW”-style design
* manipulative visual hierarchy
* unnecessary urgency

Use neutral, evidence-oriented language.

The product should help the user understand the analysis rather than push a decision.

---

# 45. FINAL VISUAL DIRECTION

The target aesthetic:

**Premium fintech + editorial research + modern AI workspace**

Think:

* sophisticated
* clean
* spacious
* data-rich but calm
* high information clarity
* excellent typography
* subtle interaction
* strong alignment
* refined components
* trustworthy visual language

Avoid:

**generic dashboard + excessive cards + excessive gradients + excessive pills + terminal-like density**

---

# 46. FIGMA AUDIT PROCESS

Do NOT immediately redesign everything.

First perform a structured audit.

### Phase 1 — Inventory

Identify:

* pages
* routes
* screens
* components
* navigation
* repeated patterns
* states
* responsive variants

### Phase 2 — UX Audit

Identify:

* friction
* cognitive overload
* unclear hierarchy
* duplicate interactions
* dead ends
* unnecessary navigation
* inconsistent terminology

### Phase 3 — Visual Audit

Inspect:

* typography
* spacing
* alignment
* color
* component consistency
* charts
* icons
* borders
* shadows
* responsiveness

### Phase 4 — Information Architecture

Propose a cleaner hierarchy.

### Phase 5 — Design System

Standardize reusable foundations.

### Phase 6 — Screen Redesign

Redesign only after the above decisions are clear.

---

# 47. FIGMA OUTPUT REQUIRED

Create a professional design-audit structure containing:

## 01 — Current Product Audit

Annotated current screens.

## 02 — UX Problems

Clearly identified friction points.

## 03 — Proposed Information Architecture

New navigation hierarchy.

## 04 — Design System

Colors, typography, spacing, radius, elevation, icons.

## 05 — Core Components

Buttons
Inputs
Search
Navigation
Metric cards
Insight cards
Charts
Source badges
Status indicators
Empty states
Loading states
Error states
Chat composer
Drawers
Modals

## 06 — Redesigned Screens

At minimum:

* Landing/search experience — preserve approved existing design
* Analysis overview
* Buffett analysis
* Financials
* Valuation
* Risk
* Deep Dive navigation
* AI follow-up state
* Loading state
* Empty state
* Error state
* Mobile analysis

## 07 — Interaction States

Show:

* default
* hover
* active
* selected
* disabled
* loading
* expanded
* collapsed
* error
* empty

---

# 48. DESIGN TOKENS

Use actual reusable Figma variables/tokens rather than manually styling every screen.

Create tokens for:

* color
* typography
* spacing
* radius
* border
* shadow/elevation
* chart semantics

Use Auto Layout consistently.

Use component variants.

Use reusable components.

Avoid manually positioned UI where Auto Layout is appropriate.

---

# 49. COMPONENT ARCHITECTURE

Components should be designed around reusable product patterns, not individual screens.

For example:

`MetricCard`

`InsightCard`

`EvidenceCard`

`TrendChart`

`ValuationRange`

`SourceBadge`

`SectionHeader`

`ExpandableInsight`

`AnalysisNavItem`

`CompanyHeader`

`FollowUpComposer`

`EmptyState`

`LoadingState`

`ErrorState`

Build components so the visual language remains consistent across the entire product.

---

# 50. IMPORTANT: DO NOT OVER-DESIGN

Do not redesign simply to demonstrate creativity.

Every change must answer one of:

* easier to understand
* faster to navigate
* easier to compare
* easier to trust
* easier to act
* more visually coherent
* more accessible
* more responsive
* less cognitively demanding

If an existing element already works well, preserve it.

---

# 51. FINAL QUALITY BAR

Before considering the redesign complete, ask:

### Can a first-time user understand the product in 30 seconds?

### Can a beginner understand the analysis?

### Can an experienced investor quickly reach detailed evidence?

### Can a user move from conclusion → evidence → explanation without losing context?

### Can the user ask a follow-up question naturally?

### Does the UI remain calm despite large amounts of financial data?

### Does every screen feel like it belongs to the same product?

### Does mobile feel intentionally designed?

### Are all states polished?

### Does the interface feel premium enough to trust with financial research?

---

# 52. MOST IMPORTANT DESIGN PRINCIPLE

Do not optimize DSP-AI-Indicator for the maximum amount of information visible on screen.

Optimize it for:

> **Maximum understanding with minimum cognitive friction.**

The user should be able to progressively move from:

**Company → Result → Why → Evidence → Detail → Question**

without feeling lost.

That should become the central UX philosophy of the product.

---

# 53. IMPLEMENTATION SAFETY

Before making frontend changes:

1. Inspect the existing implementation.
2. Identify the canonical `/analysis` route.
3. Identify protected landing-page components.
4. Identify shared components.
5. Identify existing design tokens.
6. Identify current responsive behavior.
7. Identify current component dependencies.
8. Avoid changing backend/API/data logic.
9. Avoid duplicating existing functionality.
10. Make changes incrementally.
11. Validate after each major design-system change.
12. Preserve all working functionality.

Do not perform destructive refactoring simply to make the code appear cleaner.

The objective is:

**better product experience, not unnecessary code churn.**

---

# FINAL DIRECTIVE

Approach this as if you are taking ownership of a real fintech product that already has substantial engineering behind it.

Do not behave like a visual decorator.

Behave like a **10+ year Principal Product Designer conducting a product-level UX audit**.

First understand the system.

Then identify the highest-impact problems.

Then simplify the information architecture.

Then establish the design system.

Then improve the interaction model.

Then redesign the screens.

The final experience should feel:

**Simple enough for a first-time investor.
Powerful enough for a serious investor.
Premium enough to feel trustworthy.
Interactive enough to feel AI-native.
Structured enough to feel institutional.
Calm enough to never feel overwhelming.**
