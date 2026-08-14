# DSP AI Indicator

## REP-002 — Research Ontology

Version: 1.0.0

Status: Approved

Owner: DSP Research Team

Governed By:
DSP Research Constitution v1.0

---

# Ontology Roadmap

This document is the institutional architecture map for REP-002 Version 1.0.0. It records the approved book structure, concept inventory, dependencies, and completion status.

Concept definitions are authoritative in the ontology books and catalogued in `CONCEPT_ID_REGISTRY.md` and `ontology-index.md`. This roadmap does not redefine concepts.

---

# Book 01 — Core Principles

**Status:** Complete (Approved)

## Purpose

Establish the foundational research language that governs how truth, evidence, facts, observations, assumptions, inferences, and confidence are distinguished and used across DSP AI Indicator.

## Scope

Core epistemological and analytical primitives required by every subsequent ontology book.

## Concepts (Authoritative)

| Concept ID | Concept Name |
|---|---|
| CP-001 | Truth |
| CP-002 | Evidence |
| CP-003 | Fact |
| CP-004 | Observation |
| CP-005 | Assumption |
| CP-006 | Inference |
| CP-007 | Confidence |

## Dependencies

None. Book 01 is the base layer of REP-002.

## Concept Count

7

---

# Book 02 — Research Objects

**Status:** Complete (Approved)

## Purpose

Define the enduring research artefacts and identity objects that DSP AI Indicator creates, stores, references, and revisits over time.

## Scope

Named research objects and their meaning as institutional artefacts, independent of storage technology or API shape.

## Concepts (Authoritative)

| Concept ID | Concept Name |
|---|---|
| RO-001 | Entity |
| RO-002 | Organization |
| RO-003 | Security |
| RO-004 | Financial Statement |
| RO-005 | Metric |
| RO-006 | Dataset |
| RO-007 | Source |
| RO-008 | Document |
| RO-009 | Time Period |
| RO-010 | Currency |

## Dependencies

Book 01 — Core Principles

## Concept Count

10

---

# Book 03 — Financial Ontology

**Status:** Complete (Approved)

## Purpose

Define the financial vocabulary used consistently in analysis, explanation, and validation.

## Scope

Statement elements, ratios, and financial condition concepts as meanings. Does not include calculation algorithms or scoring formulas.

## Concepts (Authoritative)

| Concept ID | Concept Name |
|---|---|
| FC-001 | Revenue |
| FC-002 | Operating Profit |
| FC-003 | Free Cash Flow |
| FC-004 | Capital Expenditure |
| FC-005 | Working Capital |
| FC-006 | Return on Capital |
| FC-007 | Return on Equity |
| FC-008 | Leverage |
| FC-009 | Interest Coverage |
| FC-010 | Earnings Quality |
| FC-011 | Cash Conversion |
| FC-012 | Capital Intensity |

## Dependencies

Book 01 — Core Principles  
Book 02 — Research Objects

## Concept Count

12

---

# Book 04 — Business Quality

**Status:** Complete (Approved)

## Purpose

Define qualitative and structural business characteristics used to judge durability and quality independent of short-term price movement.

## Scope

Business-quality meanings and related attributes. Does not include scoring engines or UI presentation.

## Concepts (Authoritative)

| Concept ID | Concept Name |
|---|---|
| BQ-001 | Business Quality |
| BQ-002 | Competitive Position |
| BQ-003 | Pricing Power |
| BQ-004 | Customer Stickiness |
| BQ-005 | Cost Advantage |
| BQ-006 | Scale Advantage |
| BQ-007 | Industry Structure |
| BQ-008 | Operating Discipline |
| BQ-009 | Capital Allocation Quality |
| BQ-010 | Reinvestment Opportunity |
| BQ-011 | Franchise Durability |
| BQ-012 | Quality Deterioration Signal |

## Dependencies

Book 01 — Core Principles  
Book 03 — Financial Ontology

## Concept Count

12

---

# Book 05 — Management

**Status:** Complete (Approved)

## Purpose

Define management quality, stewardship, and related qualitative factors used in research judgement.

## Scope

Management meanings as ontology concepts. Does not include HR systems, compensation calculators, or UI presentation.

## Concepts (Authoritative)

| Concept ID | Concept Name |
|---|---|
| MQ-001 | Management Quality |
| MQ-002 | Integrity |
| MQ-003 | Corporate Governance |
| MQ-004 | Incentive Alignment |
| MQ-005 | Leadership Quality |
| MQ-006 | Shareholder Orientation |
| MQ-007 | Transparency |
| MQ-008 | Accountability |
| MQ-009 | Execution Capability |
| MQ-010 | Long-term Stewardship |
| MQ-011 | Management Candor |
| MQ-012 | Succession Readiness |

## Dependencies

Book 01 — Core Principles  
Book 04 — Business Quality

## Concept Count

12

---

# Book 06 — Economic Moat

**Status:** Complete (Approved)

## Purpose

Define durable competitive advantage and the structural conditions that sustain or erode it.

## Scope

Moat meanings and moat-source attributes. Does not include scoring algorithms or recommendation logic.

## Concepts (Authoritative)

| Concept ID | Concept Name |
|---|---|
| EM-001 | Economic Moat |
| EM-002 | Brand Strength |
| EM-003 | Network Effects |
| EM-004 | Switching Costs |
| EM-005 | Cost-Based Moat |
| EM-006 | Intangible Assets |
| EM-007 | Regulatory Advantage |
| EM-008 | Distribution Advantage |
| EM-009 | Scale-Based Moat |
| EM-010 | Ecosystem Strength |
| EM-011 | Moat Durability |
| EM-012 | Moat Erosion |

## Dependencies

Book 01 — Core Principles  
Book 04 — Business Quality  
Book 05 — Management

## Concept Count

12

---

# Book 07 — Risk

**Status:** Complete (Approved)

## Purpose

Define risk meanings used to communicate exposure, fragility, and incomplete knowledge.

## Scope

Risk classes and related attributes as ontology concepts. Does not include risk engines or portfolio optimisers.

## Concepts (Authoritative)

| Concept ID | Concept Name |
|---|---|
| RU-001 | Business Risk |
| RU-002 | Financial Risk |
| RU-003 | Operational Risk |
| RU-004 | Industry Risk |
| RU-005 | Regulatory Risk |
| RU-006 | Governance Risk |
| RU-007 | Concentration Risk |
| RU-008 | Liquidity Risk |
| RU-009 | Currency Risk |
| RU-010 | Tail Risk |
| RU-011 | Permanent Capital Loss |
| RU-012 | Margin of Safety |

## Dependencies

Book 01 — Core Principles  
Book 03 — Financial Ontology  
Book 04 — Business Quality  
Book 05 — Management  
Book 06 — Economic Moat

## Concept Count

12

---

# Book 08 — Valuation

**Status:** Complete (Approved)

## Purpose

Define valuation vocabulary so that intrinsic value language remains consistent across models, reports, and explanations.

## Scope

Valuation meanings and comparative value concepts. Does not include model code, discount-rate algorithms, or recommendation logic.

## Concepts (Authoritative)

| Concept ID | Concept Name |
|---|---|
| VC-001 | Intrinsic Value |
| VC-002 | Fair Value |
| VC-003 | Market Value |
| VC-004 | Valuation Margin of Safety |
| VC-005 | Discount Rate |
| VC-006 | Discounted Cash Flow |
| VC-007 | Terminal Value |
| VC-008 | Relative Valuation |
| VC-009 | Residual Income Valuation |
| VC-010 | Earnings Power Value |
| VC-011 | Asset-Based Valuation |
| VC-012 | Valuation Confidence |

## Dependencies

Book 01 — Core Principles  
Book 03 — Financial Ontology  
Book 04 — Business Quality  
Book 06 — Economic Moat  
Book 07 — Risk

## Concept Count

12

---

# Book 09 — Decision Framework

**Status:** Complete (Approved)

## Purpose

Define the integration layer that combines evidence, financial analysis, quality, management, moat, risk, valuation, and governance into institutional research decisions.

## Scope

Decision-oriented research meanings under Research Mode and institutional governance. Does not prescribe brokerage behaviour or order routing.

## Concepts (Authoritative)

| Concept ID | Concept Name |
|---|---|
| DF-001 | Research Conclusion |
| DF-002 | Investment Thesis |
| DF-003 | Decision Confidence |
| DF-004 | Recommendation State |
| DF-005 | Decision Criteria |
| DF-006 | Evidence Weighting |
| DF-007 | Contradictory Evidence Handling |
| DF-008 | Scenario Analysis |
| DF-009 | Decision Review |
| DF-010 | Decision Revision |
| DF-011 | Research Lifecycle |
| DF-012 | Continuous Learning |

## Dependencies

Book 01 — Core Principles  
Book 02 — Research Objects  
Book 03 — Financial Ontology  
Book 04 — Business Quality  
Book 05 — Management  
Book 06 — Economic Moat  
Book 07 — Risk  
Book 08 — Valuation  
Book 10 — Governance & AI Intelligence

## Concept Count

12

## Layering Note

Book 09 depends on Book 10 for governance presentation concepts (for example Recommendation and Analytical Confidence Level). Numeric book order does not imply that Decision Framework precedes Governance in the dependency graph.

---

# Book 10 — Governance & AI Intelligence

**Status:** Complete (Approved)

## Purpose

Define governance and AI-intelligence meanings that protect research accountability, explainability, validation, and institutional memory.

## Scope

AI committee, explainability, recommendation presentation, confidence communication, policy, traceability, auditability, validation, and human oversight. Does not define model weights, prompts, APIs, or UI layout.

## Concepts (Authoritative)

| Concept ID | Concept Name |
|---|---|
| GV-001 | AI Committee |
| GV-002 | Explainability |
| GV-003 | Recommendation |
| GV-004 | Analytical Confidence Level |
| GV-005 | Governance Rule |
| GV-006 | Research Policy |
| GV-007 | Research Transparency |
| GV-008 | Traceability |
| GV-009 | Auditability |
| GV-010 | Decision Record |
| GV-011 | Validation Rule |
| GV-012 | Human Oversight |

## Dependencies

Book 01 — Core Principles  
Books 02–08 (consume by reference; do not redefine)

## Concept Count

12

---

# Overall Progress Table

| Book | Title | Status | Concepts |
|---|---|---|---|
| 01 | Core Principles | Complete (Approved) | 7 |
| 02 | Research Objects | Complete (Approved) | 10 |
| 03 | Financial Ontology | Complete (Approved) | 12 |
| 04 | Business Quality | Complete (Approved) | 12 |
| 05 | Management | Complete (Approved) | 12 |
| 06 | Economic Moat | Complete (Approved) | 12 |
| 07 | Risk | Complete (Approved) | 12 |
| 08 | Valuation | Complete (Approved) | 12 |
| 09 | Decision Framework | Complete (Approved) | 12 |
| 10 | Governance & AI Intelligence | Complete (Approved) | 12 |

---

# Total Concepts

| Category | Count |
|---|---|
| Approved (Books 01–10) | **113** |
| Reserved-unused prefixes (RP, ES) | 0 IDs assigned |
| **Official ontology concepts (v1.0.0)** | **113** |

---

# Book Completion Checklist

- [x] Book 01 — Core Principles
- [x] Book 02 — Research Objects
- [x] Book 03 — Financial Ontology
- [x] Book 04 — Business Quality
- [x] Book 05 — Management
- [x] Book 06 — Economic Moat
- [x] Book 07 — Risk
- [x] Book 08 — Valuation
- [x] Book 09 — Decision Framework
- [x] Book 10 — Governance & AI Intelligence

A book is Complete when its concepts are approved, registered, indexed, and free of unresolved definition conflicts under REP-002 governance.

---

# Post–v1.0 Candidates (Not in Scope)

The following domains are **explicitly out of REP-002 Version 1.0.0**. They may be authored later only through governance:

- Portfolio ontology (multi-position context beyond Decision Framework / Governance references)
- Standalone Prediction book (forecast language remains constrained by Book 01 and Decision Framework scenarios)
- Standalone Validation book (validation meanings live primarily in GV-011 and related governance concepts)
- Standalone Company Ontology book (issuer identity covered by Research Objects)
- Standalone AI Intelligence book (merged into Book 10 — Governance & AI Intelligence)

Placeholder files for these domains, if present, are deprecated stubs and must not be treated as v1.0 concept homes.
