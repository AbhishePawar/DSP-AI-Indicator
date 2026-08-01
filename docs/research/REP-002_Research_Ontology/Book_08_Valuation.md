# DSP AI Indicator

## REP-002 — Research Ontology

Version: 1.0.0

Status: Approved
Owner: DSP Research Team

Governed By:
DSP Research Constitution v1.0

---

# Book 08 — Valuation

## Purpose

Define the institutional Valuation vocabulary used to express intrinsic worth, market comparison, valuation methods, and valuation confidence consistently across DSP AI Indicator engines, reports, explainability, and AI Committee workflows.

## Scope

Valuation meanings and comparative value concepts as ontology definitions. This book does not redefine Financial Ontology, Business Quality, Management, Economic Moat, or Risk concepts. Margin of Safety as risk mitigation remains owned by RU-012; this book defines Valuation Margin of Safety as the valuation-perspective application that references RU-012 without redefining it. This book does not include model code, discount-rate algorithms, recommendation logic, API contracts, or user-interface presentation.

## Relationship to Prior Books

Book 08 consumes Book 01 — Core Principles, Book 02 — Research Objects, Book 03 — Financial Ontology, Book 04 — Business Quality, Book 05 — Management, Book 06 — Economic Moat, and Book 07 — Risk. Valuation concepts must preserve epistemological distinctions from Book 01, remain anchored to research objects, consume financial meanings from Book 03, and interpret quality, management, moat, and risk evidence without redefining those books.

## Dependencies

- Book 01 — Core Principles
- Book 02 — Research Objects
- Book 03 — Financial Ontology
- Book 04 — Business Quality
- Book 05 — Management
- Book 06 — Economic Moat
- Book 07 — Risk

## Book Status

Approved

## Version

0.1.0

## Concepts

---

# Concept Metadata

| Field | Value |
|---|---|
| Concept ID | VC-001 |
| Concept Name | Intrinsic Value |
| Category | Valuation Concept |
| Ontology Book | Book 08 — Valuation |
| Status | Approved |
| Version | 1.0.0 |
| Author | DSP Research Team |
| Reviewer | DSP Research Team |
| Approved Date | 2026-08-01 |

---

# Core Definition

## Definition

Intrinsic value is an estimate of the present worth of an asset’s expected future economic benefits to its owner, based on evidence, assumptions, and an explicit valuation approach. Within DSP AI Indicator, intrinsic value is the foundational valuation concept used to express research estimates of worth independent of short-term market quotation.

## Purpose

Intrinsic value provides the worth-estimate lens required to compare economic value with market price and to support research, explainability, and decision workflows.

## Why It Matters

Investment research requires a concept of worth distinct from quoted price. Correctly defining intrinsic value enables consistent valuation language across engines and reports without treating any single model output as truth.

---

# Characteristics

## Characteristics

Intrinsic value should be:

- Estimate-based, not observed market fact
- Approach-explicit
- Assumption-dependent
- Evidence-anchored
- Expressible as a point, range, or scenario set
- Separated from recommendation conclusions

## What It Is Not

Intrinsic value is not:

- Market value by itself
- A guaranteed realizable price
- A recommendation
- Business quality by itself
- An Economic Moat
- Exact mathematical truth

---

# Evidence

## Evidence Requirements

Intrinsic value estimates should be supported by:

- Financial statement and cash-flow evidence
- Business quality and moat context
- Explicit assumptions and scenarios
- Discount-rate or capitalization rationale where used
- Method identification
- Confidence and limitation statements

## Confidence Drivers

Confidence increases when:

- Evidence is strong and consistent.
- Assumptions are conservative and disclosed.
- Multiple methods converge.
- Business durability is well supported.
- Uncertainty is explicitly labeled.

## Validation

Intrinsic value is validated through:

- Method and assumption disclosure checks
- Evidence linkage review
- Cross-method coherence tests
- Source confirmation
- Confidence labeling review
- Separation from market-price identity

---

# Relationships

## Related Concepts

- VC-003 Market Value
- VC-004 Valuation Margin of Safety
- VC-006 Discounted Cash Flow
- VC-012 Valuation Confidence
- FC-003 Free Cash Flow
- BQ-001 Business Quality
- EM-001 Economic Moat
- RU-012 Margin of Safety
- CP-005 Assumption
- CP-007 Confidence

## Dependencies

Depends on:

- Book 01 — Core Principles
- Book 03 — Financial Ontology
- RO-003 Security

## Successor Concepts

Supports:

- Valuation Margin of Safety
- Discounted Cash Flow
- Relative Valuation
- Recommendation Context
- Explainability
- AI Committee Review
- Portfolio Analytics

---

# Research Guidance

## Research Implication

Every intrinsic value figure used in DSP AI Indicator shall declare method, key assumptions, and confidence so that users can distinguish research estimates from market quotations and from recommendations.

## Examples

Examples include:

- DCF-derived intrinsic value range
- Earnings-power-based intrinsic estimate
- Asset-based intrinsic floor
- Scenario-weighted intrinsic value
- Single-point intrinsic estimate with undisclosed assumptions

## Limitations

Intrinsic value is inherently uncertain and model-dependent. It can be wrong even when process quality is high and must not be confused with realizable liquidation proceeds.

---

# Governance

## Revision History

Version: 1.0.0

Status: Approved
Created By: DSP Research Team

## Review Notes

Initial institutional definition for REP-002.

---

# Concept Metadata

| Field | Value |
|---|---|
| Concept ID | VC-002 |
| Concept Name | Fair Value |
| Category | Valuation Concept |
| Ontology Book | Book 08 — Valuation |
| Status | Approved |
| Version | 1.0.0 |
| Author | DSP Research Team |
| Reviewer | DSP Research Team |
| Approved Date | 2026-08-01 |

---

# Core Definition

## Definition

Fair value is an exit-oriented estimate of the price that would be received to sell an asset or paid to transfer a liability in an orderly transaction between market participants at the measurement date, according to an explicit fair-value framework. Within DSP AI Indicator, fair value is a valuation concept used when market-participant pricing, rather than owner-intrinsic worth, is the relevant measurement objective.

## Purpose

Fair value provides the market-participant pricing lens required for contexts where orderly-exit assumptions and observable inputs dominate.

## Why It Matters

Fair value and intrinsic value can diverge. Correct definition prevents conflating accounting or market-participant fair value with Buffett-style intrinsic worth.

---

# Characteristics

## Characteristics

Fair value should be:

- Market-participant oriented
- Measurement-date specific
- Input-hierarchy aware where applicable
- Distinct from entity-specific intrinsic value
- Explicit about orderly-transaction assumptions
- Evidence-based

## What It Is Not

Fair value is not:

- Intrinsic value by definition
- Distressed forced-sale price
- A recommendation
- Business quality
- Exact future transaction certainty
- An investment recommendation

---

# Evidence

## Evidence Requirements

Fair value estimates should be supported by:

- Observable market inputs where available
- Comparable transaction evidence
- Valuation technique disclosure
- Input hierarchy or reliability notes
- Measurement-date context
- Adjustments for non-orderly conditions when relevant

## Confidence Drivers

Confidence increases when:

- Observable inputs are high quality.
- Markets are orderly and active.
- Techniques are standard and disclosed.
- Adjustments are transparent.
- Independent evidence agrees.

## Validation

Fair value is validated through:

- Input observability review
- Technique disclosure checks
- Orderly-market assumption review
- Source confirmation
- Distinction from intrinsic-value estimates
- Measurement-date consistency

---

# Relationships

## Related Concepts

- VC-001 Intrinsic Value
- VC-003 Market Value
- VC-008 Relative Valuation
- RO-003 Security
- CP-002 Evidence
- CP-007 Confidence

## Dependencies

Depends on:

- Book 01 — Core Principles
- VC-001 Intrinsic Value

## Successor Concepts

Supports:

- Relative Valuation
- Reporting and Disclosure Context
- Explainability
- AI Committee Review
- Portfolio Analytics
- Cross-Method Comparison
- Research Reports

---

# Research Guidance

## Research Implication

Research surfaces shall label fair value distinctly from intrinsic value and shall not present fair-value outputs as owner-intrinsic worth without explicit qualification.

## Examples

Examples include:

- Mark-to-market fair value of a liquid security
- Level-2 comparable-based fair value
- Model-based fair value with significant unobservable inputs
- Intrinsic value estimate intentionally different from fair value
- Distressed transaction mislabeled as fair value

## Limitations

Fair value depends on market conditions and participant assumptions. In inactive or disordered markets, fair value uncertainty rises sharply.

---

# Governance

## Revision History

Version: 1.0.0

Status: Approved
Created By: DSP Research Team

## Review Notes

Initial institutional definition for REP-002.

---

# Concept Metadata

| Field | Value |
|---|---|
| Concept ID | VC-003 |
| Concept Name | Market Value |
| Category | Valuation Concept |
| Ontology Book | Book 08 — Valuation |
| Status | Approved |
| Version | 1.0.0 |
| Author | DSP Research Team |
| Reviewer | DSP Research Team |
| Approved Date | 2026-08-01 |

---

# Core Definition

## Definition

Market value is the observed or readily quotable exchange value of an asset in the market at a stated time, typically represented by market price and related market capitalization measures. Within DSP AI Indicator, market value is a valuation concept used as the factual market reference against which research estimates of worth are compared.

## Purpose

Market value provides the observed-price lens required to anchor value-versus-price analysis and portfolio market exposure.

## Why It Matters

Research decisions compare worth estimates with what the market currently offers. Correct definition keeps market quotations factual and distinct from intrinsic estimates.

---

# Characteristics

## Characteristics

Market value should be:

- Market-observed or market-quoted
- Timestamped
- Venue- and currency-aware
- Distinct from intrinsic value
- Sensitive to liquidity conditions
- Traceable to market data sources

## What It Is Not

Market value is not:

- Intrinsic value
- Fair value in every accounting sense
- A statement of true worth
- A recommendation
- Permanent capital value
- An investment recommendation

---

# Evidence

## Evidence Requirements

Market value observations should be supported by:

- Exchange or market-data quotes
- Timestamp and venue identifiers
- Currency denomination
- Corporate-action adjustments where relevant
- Liquidity context
- Source attribution

## Confidence Drivers

Confidence increases when:

- Markets are liquid and continuous.
- Quotes are from authoritative venues.
- Timestamps are precise.
- Corporate actions are correctly handled.
- Independent feeds agree.

## Validation

Market value is validated through:

- Source and timestamp verification
- Currency and corporate-action checks
- Liquidity-context review
- Cross-feed reconciliation
- Separation from estimate labels
- Stale-quote screening

---

# Relationships

## Related Concepts

- VC-001 Intrinsic Value
- VC-004 Valuation Margin of Safety
- RO-003 Security
- RO-010 Currency
- RU-008 Liquidity Risk
- CP-003 Fact
- CP-002 Evidence

## Dependencies

Depends on:

- Book 01 — Core Principles
- RO-003 Security
- RO-010 Currency

## Successor Concepts

Supports:

- Valuation Margin of Safety
- Relative Valuation
- Portfolio Market Exposure
- Explainability
- AI Committee Review
- Research Reports
- Value vs Price Comparison

---

# Research Guidance

## Research Implication

Market value shall be presented as observed market information with time and source context, never as proof of intrinsic worth.

## Examples

Examples include:

- Last traded equity price
- Mid-market quote for a liquid bond
- Market capitalization from shares outstanding and price
- Stale quote in an illiquid security
- Indicative quote mislabeled as firm market value

## Limitations

Market value can be distorted by low liquidity, temporary dislocations, or incomplete quotes. Observation quality varies by venue and instrument.

---

# Governance

## Revision History

Version: 1.0.0

Status: Approved
Created By: DSP Research Team

## Review Notes

Initial institutional definition for REP-002.

---

# Concept Metadata

| Field | Value |
|---|---|
| Concept ID | VC-004 |
| Concept Name | Valuation Margin of Safety |
| Category | Valuation Concept |
| Ontology Book | Book 08 — Valuation |
| Status | Approved |
| Version | 1.0.0 |
| Author | DSP Research Team |
| Reviewer | DSP Research Team |
| Approved Date | 2026-08-01 |

---

# Core Definition

## Definition

Valuation margin of safety is the valuation-perspective protective gap between estimated intrinsic value and market value that reduces the consequence of estimation error. Within DSP AI Indicator, this concept applies RU-012 Margin of Safety as risk-mitigation context and does not redefine RU-012; it specifies the value-versus-price expression used in valuation analysis.

## Purpose

Valuation margin of safety provides the price-to-worth buffer lens required to relate intrinsic estimates to market quotations under uncertainty.

## Why It Matters

Valuation estimates are uncertain. Correctly separating the risk-mitigation meaning (RU-012) from the valuation-perspective gap prevents duplicate ontology definitions while supporting Buffett-style caution in valuation workflows.

---

# Characteristics

## Characteristics

Valuation margin of safety should be:

- Defined relative to intrinsic value and market value
- Explicit about estimate uncertainty
- Referential to RU-012 as risk mitigation
- Distinct from a fixed universal percentage rule
- Method-aware
- Non-recommendatory by itself

## What It Is Not

Valuation margin of safety is not:

- A redefinition of RU-012 Margin of Safety
- A complete valuation model
- A guaranteed profit
- A mandatory discount formula
- Business quality by itself
- An investment recommendation

---

# Evidence

## Evidence Requirements

Valuation margin of safety assessments should be supported by:

- Explicit intrinsic value estimate or range
- Observed market value
- Key assumption and confidence disclosures
- Risk context referencing RU-012 where relevant
- Method identification
- Uncertainty and limitation statements

## Confidence Drivers

Confidence increases when:

- Intrinsic estimate quality is high.
- Market value is reliable.
- Uncertainty is frankly disclosed.
- Protective gap is meaningful relative to risks.
- Independent review agrees the comparison is coherent.

## Validation

Valuation margin of safety is validated through:

- Intrinsic-versus-market linkage checks
- Non-redefinition check against RU-012
- Assumption and confidence disclosure review
- Source confirmation
- Separation from recommendation language
- Method transparency tests

---

# Relationships

## Related Concepts

- RU-012 Margin of Safety
- VC-001 Intrinsic Value
- VC-003 Market Value
- VC-012 Valuation Confidence
- RU-011 Permanent Capital Loss
- CP-005 Assumption
- CP-007 Confidence

## Dependencies

Depends on:

- Book 01 — Core Principles
- VC-001 Intrinsic Value
- VC-003 Market Value
- RU-012 Margin of Safety

## Successor Concepts

Supports:

- Recommendation Context
- Position Sizing Context
- Explainability
- AI Committee Review
- Research Reports
- Portfolio Decision Support
- Valuation Confidence Interpretation

---

# Research Guidance

## Research Implication

When valuation workflows discuss margin of safety, they shall use Valuation Margin of Safety for value-versus-price buffers and reference RU-012 for the broader risk-mitigation meaning, never silently merging the two definitions.

## Examples

Examples include:

- Market price well below a conservative intrinsic range
- Narrow gap when estimate uncertainty is high
- Large apparent gap based on aggressive assumptions
- Explicit dual reference to RU-012 and value-price gap
- Treating any discount to peer multiples as margin of safety

## Limitations

A large valuation gap can reflect model error rather than opportunity. Protective gaps do not eliminate permanent capital loss risk.

---

# Governance

## Revision History

Version: 1.0.0

Status: Approved
Created By: DSP Research Team

## Review Notes

Initial institutional definition for REP-002.

---

# Concept Metadata

| Field | Value |
|---|---|
| Concept ID | VC-005 |
| Concept Name | Discount Rate |
| Category | Valuation Concept |
| Ontology Book | Book 08 — Valuation |
| Status | Approved |
| Version | 1.0.0 |
| Author | DSP Research Team |
| Reviewer | DSP Research Team |
| Approved Date | 2026-08-01 |

---

# Core Definition

## Definition

A discount rate is the rate used to translate expected future economic benefits into present value, reflecting time value and risk adjustments appropriate to the valuation approach and claim being valued. Within DSP AI Indicator, discount rate is a valuation concept used as an explicit assumption input, not as a hidden engine constant.

## Purpose

Discount rate provides the present-value translation lens required for discounted valuation methods and transparent assumption control.

## Why It Matters

Small discount-rate changes can dominate valuation outputs. Correct definition forces disclosure and prevents treating the rate as unexplained authority.

---

# Characteristics

## Characteristics

A discount rate should be:

- Explicitly stated
- Approach-consistent
- Risk- and claim-aware
- Comparable only under like definitions
- Separated from recommendation outputs
- Evidence- and judgment-informed

## What It Is Not

A discount rate is not:

- Intrinsic value itself
- A market price
- A guarantee of required investor return realization
- Business quality
- An opaque default with no rationale
- An investment recommendation

---

# Evidence

## Evidence Requirements

Discount-rate choices should be supported by:

- Stated methodology rationale
- Risk factors considered
- Capital-structure or claim context where relevant
- Comparability notes versus alternatives
- Sensitivity disclosures
- Consistency with valuation approach

## Confidence Drivers

Confidence increases when:

- Rationale is transparent.
- Risk adjustments are coherent.
- Sensitivities are shown.
- Approach consistency is maintained.
- Independent review finds the logic plausible.

## Validation

Discount rates are validated through:

- Disclosure completeness checks
- Approach-consistency review
- Sensitivity presentation
- Source and rationale confirmation
- Separation from hidden defaults
- Cross-scenario coherence

---

# Relationships

## Related Concepts

- VC-006 Discounted Cash Flow
- VC-007 Terminal Value
- VC-001 Intrinsic Value
- RU-002 Financial Risk
- CP-005 Assumption
- CP-007 Confidence

## Dependencies

Depends on:

- Book 01 — Core Principles
- VC-001 Intrinsic Value

## Successor Concepts

Supports:

- Discounted Cash Flow
- Terminal Value
- Residual Income Valuation
- Explainability
- AI Committee Review
- Sensitivity Analysis
- Research Reports

---

# Research Guidance

## Research Implication

Every discounted valuation in DSP AI Indicator shall expose the discount rate and its rationale so that users can assess assumption sensitivity.

## Examples

Examples include:

- Cost-of-equity discount rate for equity cash flows
- WACC-style rate for firm cash flows where used
- Higher rate under elevated uncertainty
- Undisclosed engine default rate
- Scenario-specific rates with stated logic

## Limitations

Discount rates are judgment-heavy and not uniquely determined by data. False precision is a common failure mode.

---

# Governance

## Revision History

Version: 1.0.0

Status: Approved
Created By: DSP Research Team

## Review Notes

Initial institutional definition for REP-002.

---

# Concept Metadata

| Field | Value |
|---|---|
| Concept ID | VC-006 |
| Concept Name | Discounted Cash Flow |
| Category | Valuation Concept |
| Ontology Book | Book 08 — Valuation |
| Status | Approved |
| Version | 1.0.0 |
| Author | DSP Research Team |
| Reviewer | DSP Research Team |
| Approved Date | 2026-08-01 |

---

# Core Definition

## Definition

Discounted cash flow is a valuation approach that estimates present worth by projecting expected cash flows and discounting them at an explicit discount rate, often including a terminal value component. Within DSP AI Indicator, discounted cash flow is a valuation-method concept used to structure cash-flow-based intrinsic estimates.

## Purpose

Discounted cash flow provides the cash-flow present-value method lens required for transparent multi-period valuation analysis.

## Why It Matters

Cash-flow-based methods are central to intrinsic valuation. Correct definition standardizes method language without prescribing engine algorithms.

---

# Characteristics

## Characteristics

Discounted cash flow should be:

- Cash-flow based
- Projection-explicit
- Discount-rate explicit
- Terminal-value aware where used
- Assumption-transparent
- Distinct from relative valuation

## What It Is Not

Discounted cash flow is not:

- Market value by itself
- Relative valuation
- A recommendation
- Guaranteed forecast accuracy
- A single mandatory formula
- An investment recommendation

---

# Evidence

## Evidence Requirements

Discounted cash flow applications should be supported by:

- Cash-flow definitions and projections
- Explicit discount rate
- Terminal value method where used
- Key business and financial assumptions
- Scenario or sensitivity analysis
- Confidence and limitation statements

## Confidence Drivers

Confidence increases when:

- Cash-flow definitions are clear.
- Assumptions are evidence-linked.
- Sensitivities are disclosed.
- Terminal value is not opaque.
- Independent review finds coherence.

## Validation

Discounted cash flow is validated through:

- Cash-flow definition checks
- Assumption disclosure review
- Discount-rate and terminal-value transparency
- Source confirmation
- Sensitivity completeness
- Separation from recommendation outputs

---

# Relationships

## Related Concepts

- VC-001 Intrinsic Value
- VC-005 Discount Rate
- VC-007 Terminal Value
- FC-003 Free Cash Flow
- VC-012 Valuation Confidence
- CP-005 Assumption
- CP-006 Inference
- CP-007 Confidence

## Dependencies

Depends on:

- Book 01 — Core Principles
- VC-001 Intrinsic Value
- VC-005 Discount Rate
- FC-003 Free Cash Flow

## Successor Concepts

Supports:

- Intrinsic Value Estimation
- Terminal Value Analysis
- Explainability
- AI Committee Review
- Research Reports
- Cross-Method Comparison
- Sensitivity Workflows

---

# Research Guidance

## Research Implication

Discounted cash flow outputs shall be labeled as method-based estimates with disclosed cash-flow definitions, rates, and terminal assumptions.

## Examples

Examples include:

- Free-cash-flow-to-firm DCF
- Free-cash-flow-to-equity DCF
- Multi-stage DCF with explicit fade
- DCF dominated by opaque terminal value
- Scenario DCF with bull, base, and bear cases

## Limitations

Projection error and terminal-value dominance can overwhelm apparent precision. DCF quality depends on assumption integrity more than spreadsheet complexity.

---

# Governance

## Revision History

Version: 1.0.0

Status: Approved
Created By: DSP Research Team

## Review Notes

Initial institutional definition for REP-002.

---

# Concept Metadata

| Field | Value |
|---|---|
| Concept ID | VC-007 |
| Concept Name | Terminal Value |
| Category | Valuation Concept |
| Ontology Book | Book 08 — Valuation |
| Status | Approved |
| Version | 1.0.0 |
| Author | DSP Research Team |
| Reviewer | DSP Research Team |
| Approved Date | 2026-08-01 |

---

# Core Definition

## Definition

Terminal value is the estimated value attributed to cash flows or residual worth beyond the explicit forecast horizon in a multi-period valuation. Within DSP AI Indicator, terminal value is a valuation concept used to make long-horizon residual worth explicit and inspectable.

## Purpose

Terminal value provides the continuing-value lens required to complete multi-period valuations without hiding the bulk of estimated worth.

## Why It Matters

Terminal value often dominates DCF results. Correct definition forces transparency about continuing-value assumptions and their uncertainty.

---

# Characteristics

## Characteristics

Terminal value should be:

- Horizon-linked
- Method-explicit
- Assumption-transparent
- Sensitivitized where material
- Distinct from explicit-period cash flows
- Confidence-labeled

## What It Is Not

Terminal value is not:

- A market quote
- Proof of perpetual high growth
- A recommendation
- Intrinsic value by itself
- An unexplained residual plug
- An investment recommendation

---

# Evidence

## Evidence Requirements

Terminal value estimates should be supported by:

- Explicit horizon definition
- Continuing-value method disclosure
- Growth, fade, or exit-multiple assumptions
- Consistency with long-term economics
- Sensitivity analysis
- Limitation statements

## Confidence Drivers

Confidence increases when:

- Method is disclosed.
- Long-term assumptions are conservative and coherent.
- Sensitivities are shown.
- Fade or normalization logic is credible.
- Independent review agrees.

## Validation

Terminal value is validated through:

- Method disclosure checks
- Assumption coherence review
- Dominance and sensitivity analysis
- Source confirmation
- Consistency with business durability evidence
- Explicit uncertainty labeling

---

# Relationships

## Related Concepts

- VC-006 Discounted Cash Flow
- VC-005 Discount Rate
- VC-001 Intrinsic Value
- EM-011 Moat Durability
- CP-005 Assumption
- CP-007 Confidence

## Dependencies

Depends on:

- Book 01 — Core Principles
- VC-006 Discounted Cash Flow

## Successor Concepts

Supports:

- Discounted Cash Flow Completeness
- Valuation Confidence
- Explainability
- AI Committee Review
- Research Reports
- Sensitivity Analysis
- Long-Horizon Uncertainty Communication

---

# Research Guidance

## Research Implication

Terminal value shall never be an unexplained residual. Research outputs shall state method, key continuing-value assumptions, and contribution to total estimated value.

## Examples

Examples include:

- Gordon growth terminal value
- Exit-multiple terminal value
- Fade-to-normal-return terminal value
- Terminal value comprising most of enterprise value
- Perpetual hyper-growth terminal assumption

## Limitations

Long-horizon uncertainty is irreducible. Terminal value can create false precision if growth and return assumptions are heroic.

---

# Governance

## Revision History

Version: 1.0.0

Status: Approved
Created By: DSP Research Team

## Review Notes

Initial institutional definition for REP-002.

---

# Concept Metadata

| Field | Value |
|---|---|
| Concept ID | VC-008 |
| Concept Name | Relative Valuation |
| Category | Valuation Concept |
| Ontology Book | Book 08 — Valuation |
| Status | Approved |
| Version | 1.0.0 |
| Author | DSP Research Team |
| Reviewer | DSP Research Team |
| Approved Date | 2026-08-01 |

---

# Core Definition

## Definition

Relative valuation is a valuation approach that estimates or interprets value by comparing an asset with peer assets or its own history using ratios or multiples based on earnings, cash flow, book value, revenue, or other bases. Within DSP AI Indicator, relative valuation is a valuation-method concept used for comparative value analysis.

## Purpose

Relative valuation provides the comparative-pricing lens required to interpret value in peer and historical context.

## Why It Matters

Markets often price through comparables. Correct definition enables transparent multiple-based analysis without confusing it with intrinsic cash-flow worth.

---

# Characteristics

## Characteristics

Relative valuation should be:

- Peer- or history-based
- Multiple-definition explicit
- Comparability-aware
- Distinct from DCF intrinsic methods
- Assumption-transparent about peer set
- Non-recommendatory by itself

## What It Is Not

Relative valuation is not:

- Intrinsic value by definition
- Proof that the peer set is correctly priced
- A recommendation
- Business quality
- Exact fair worth
- An investment recommendation

---

# Evidence

## Evidence Requirements

Relative valuation applications should be supported by:

- Explicit multiple definitions
- Peer-set or history definition
- Basis metrics from financial evidence
- Comparability adjustments where used
- Dispersion and outlier handling notes
- Limitation statements

## Confidence Drivers

Confidence increases when:

- Peers are genuinely comparable.
- Multiple definitions are standard and clear.
- Adjustments are transparent.
- Cross-checks with other methods exist.
- Independent review agrees.

## Validation

Relative valuation is validated through:

- Peer-set appropriateness review
- Multiple-definition checks
- Comparability screening
- Source confirmation
- Outlier sensitivity review
- Separation from intrinsic-value claims

---

# Relationships

## Related Concepts

- VC-002 Fair Value
- VC-003 Market Value
- VC-001 Intrinsic Value
- FC-001 Revenue
- FC-002 Operating Profit
- CP-002 Evidence
- CP-007 Confidence

## Dependencies

Depends on:

- Book 01 — Core Principles
- VC-003 Market Value
- Book 03 — Financial Ontology

## Successor Concepts

Supports:

- Cross-Method Comparison
- Explainability
- AI Committee Review
- Research Reports
- Screening Context
- Portfolio Analytics
- Fair Value Context

---

# Research Guidance

## Research Implication

Relative valuation outputs shall disclose the multiple, basis, and peer or history set, and shall not be labeled intrinsic value without additional method support.

## Examples

Examples include:

- Peer P/E comparison
- EV/EBITDA sector multiples
- Price-to-book for financials
- Historical multiple reversion analysis
- Peer set mixing incompatible business models

## Limitations

Relative valuation inherits peer mispricing and comparability error. Cheap versus peers is not automatically undervalued intrinsically.

---

# Governance

## Revision History

Version: 1.0.0

Status: Approved
Created By: DSP Research Team

## Review Notes

Initial institutional definition for REP-002.

---

# Concept Metadata

| Field | Value |
|---|---|
| Concept ID | VC-009 |
| Concept Name | Residual Income Valuation |
| Category | Valuation Concept |
| Ontology Book | Book 08 — Valuation |
| Status | Approved |
| Version | 1.0.0 |
| Author | DSP Research Team |
| Reviewer | DSP Research Team |
| Approved Date | 2026-08-01 |

---

# Core Definition

## Definition

Residual income valuation is a valuation approach that estimates worth from book value plus the present value of expected residual income, where residual income is earnings in excess of a required return on book capital. Within DSP AI Indicator, residual income valuation is a valuation-method concept used as an accounting-linked intrinsic approach.

## Purpose

Residual income valuation provides the book-plus-excess-earnings method lens required for transparent accounting-based intrinsic analysis.

## Why It Matters

Residual income methods connect accounting carrying values with expected economic excess returns. Correct definition standardizes this method language without prescribing engine implementation.

---

# Characteristics

## Characteristics

Residual income valuation should be:

- Book-value anchored
- Residual-income explicit
- Required-return explicit
- Horizon- and continuing-value aware
- Assumption-transparent
- Distinct from pure relative multiples

## What It Is Not

Residual income valuation is not:

- Book value alone
- Relative valuation
- A recommendation
- Guaranteed accounting truth
- Discounted cash flow by another name in all cases
- An investment recommendation

---

# Evidence

## Evidence Requirements

Residual income applications should be supported by:

- Book value definitions
- Earnings definitions
- Required-return rationale
- Residual income projections
- Continuing-value treatment
- Accounting-quality caveats

## Confidence Drivers

Confidence increases when:

- Accounting bases are clean and disclosed.
- Required return is justified.
- Residual income drivers are evidence-linked.
- Sensitivities are shown.
- Independent review finds coherence.

## Validation

Residual income valuation is validated through:

- Accounting-base disclosure checks
- Required-return transparency
- Projection coherence review
- Source confirmation
- Earnings-quality caveats
- Separation from recommendation outputs

---

# Relationships

## Related Concepts

- VC-001 Intrinsic Value
- VC-005 Discount Rate
- VC-010 Earnings Power Value
- FC-007 Return on Equity
- FC-010 Earnings Quality
- CP-005 Assumption
- CP-007 Confidence

## Dependencies

Depends on:

- Book 01 — Core Principles
- VC-001 Intrinsic Value
- Book 03 — Financial Ontology

## Successor Concepts

Supports:

- Intrinsic Value Estimation
- Cross-Method Comparison
- Explainability
- AI Committee Review
- Research Reports
- Accounting-Based Valuation Context
- Sensitivity Workflows

---

# Research Guidance

## Research Implication

Residual income outputs shall disclose book base, earnings base, required return, and continuing-value treatment, with earnings-quality caveats where material.

## Examples

Examples include:

- Clean-surplus residual income model
- Multi-stage residual income with fade
- Bank valuation using residual income logic
- Residual income ignoring accounting distortions
- Residual income reconciled to DCF under clean surplus

## Limitations

Accounting distortions and dirty surplus items can impair residual income reliability. Method quality depends on earnings and book integrity.

---

# Governance

## Revision History

Version: 1.0.0

Status: Approved
Created By: DSP Research Team

## Review Notes

Initial institutional definition for REP-002.

---

# Concept Metadata

| Field | Value |
|---|---|
| Concept ID | VC-010 |
| Concept Name | Earnings Power Value |
| Category | Valuation Concept |
| Ontology Book | Book 08 — Valuation |
| Status | Approved |
| Version | 1.0.0 |
| Author | DSP Research Team |
| Reviewer | DSP Research Team |
| Approved Date | 2026-08-01 |

---

# Core Definition

## Definition

Earnings power value is a valuation estimate of worth based on sustainable earning power capitalized at an appropriate rate, emphasizing normalized earnings capacity rather than speculative growth. Within DSP AI Indicator, earnings power value is a valuation-method concept used for earnings-capacity-based intrinsic analysis.

## Purpose

Earnings power value provides the normalized-earnings capitalization lens required to estimate worth from durable earning capacity.

## Why It Matters

Growth assumptions can dominate and distort valuations. Correct definition supports conservative earnings-power analysis grounded in sustainable results and earnings quality.

---

# Characteristics

## Characteristics

Earnings power value should be:

- Normalized-earnings based
- Capitalization-rate explicit
- Growth-modest or growth-separated
- Earnings-quality aware
- Assumption-transparent
- Distinct from pure relative multiples

## What It Is Not

Earnings power value is not:

- Peak-cycle earnings capitalized uncritically
- A growth-story DCF substitute without disclosure
- A recommendation
- Market value
- Guaranteed sustainable earnings
- An investment recommendation

---

# Evidence

## Evidence Requirements

Earnings power value applications should be supported by:

- Normalized earnings construction
- Earnings quality assessment
- Capitalization or discount-rate rationale
- Adjustments for one-time items
- Cycle-context notes
- Limitation statements

## Confidence Drivers

Confidence increases when:

- Normalization is evidence-based.
- Earnings quality is high.
- Cycle adjustments are transparent.
- Rate rationale is clear.
- Independent review agrees.

## Validation

Earnings power value is validated through:

- Normalization disclosure checks
- Earnings-quality linkage
- Rate transparency review
- Source confirmation
- Peak/trough screening
- Separation from recommendation outputs

---

# Relationships

## Related Concepts

- VC-001 Intrinsic Value
- VC-005 Discount Rate
- FC-002 Operating Profit
- FC-010 Earnings Quality
- BQ-001 Business Quality
- CP-005 Assumption
- CP-007 Confidence

## Dependencies

Depends on:

- Book 01 — Core Principles
- VC-001 Intrinsic Value
- FC-010 Earnings Quality

## Successor Concepts

Supports:

- Intrinsic Value Estimation
- Cross-Method Comparison
- Explainability
- AI Committee Review
- Research Reports
- Conservative Valuation Context
- Sensitivity Workflows

---

# Research Guidance

## Research Implication

Earnings power value outputs shall disclose how normalized earnings were constructed and why the capitalization rate is appropriate.

## Examples

Examples include:

- Mid-cycle EBIT capitalization
- Owner-earnings power estimate
- Adjusted earnings excluding one-time gains
- Peak-margin earnings capitalized as “normal”
- Earnings power cross-checked against DCF

## Limitations

Normalization is judgmental. Structural change can invalidate historical earning power quickly.

---

# Governance

## Revision History

Version: 1.0.0

Status: Approved
Created By: DSP Research Team

## Review Notes

Initial institutional definition for REP-002.

---

# Concept Metadata

| Field | Value |
|---|---|
| Concept ID | VC-011 |
| Concept Name | Asset-Based Valuation |
| Category | Valuation Concept |
| Ontology Book | Book 08 — Valuation |
| Status | Approved |
| Version | 1.0.0 |
| Author | DSP Research Team |
| Reviewer | DSP Research Team |
| Approved Date | 2026-08-01 |

---

# Core Definition

## Definition

Asset-based valuation is a valuation approach that estimates worth by reference to the value of assets and liabilities, such as adjusted book value, net asset value, or orderly liquidation concepts. Within DSP AI Indicator, asset-based valuation is a valuation-method concept used for asset-anchored worth estimates.

## Purpose

Asset-based valuation provides the net-asset lens required when asset coverage, floors, or liquidation contexts are analytically relevant.

## Why It Matters

For some businesses and stress contexts, asset coverage matters as much as earnings power. Correct definition standardizes asset-anchored valuation language without prescribing appraisal algorithms.

---

# Characteristics

## Characteristics

Asset-based valuation should be:

- Asset- and liability-anchored
- Adjustment-explicit
- Premise-explicit (going concern vs liquidation where used)
- Distinct from earnings-power methods
- Assumption-transparent
- Evidence-based

## What It Is Not

Asset-based valuation is not:

- Unadjusted accounting book value by mandate
- Intrinsic cash-flow value by definition
- A recommendation
- Market value
- Guaranteed realizable proceeds
- An investment recommendation

---

# Evidence

## Evidence Requirements

Asset-based valuation applications should be supported by:

- Asset and liability inventories
- Adjustment rationale for carrying values
- Valuation premise disclosure
- Appraisal or market-input evidence where used
- Encumbrance and liquidity notes
- Limitation statements

## Confidence Drivers

Confidence increases when:

- Asset marks are evidence-based.
- Liabilities are complete.
- Premise is appropriate.
- Encumbrances are recognized.
- Independent review agrees.

## Validation

Asset-based valuation is validated through:

- Completeness of assets and liabilities
- Adjustment transparency review
- Premise consistency checks
- Source confirmation
- Realizability caveats
- Separation from recommendation outputs

---

# Relationships

## Related Concepts

- VC-001 Intrinsic Value
- VC-002 Fair Value
- RO-004 Financial Statement
- RU-008 Liquidity Risk
- CP-002 Evidence
- CP-007 Confidence

## Dependencies

Depends on:

- Book 01 — Core Principles
- VC-001 Intrinsic Value
- RO-004 Financial Statement

## Successor Concepts

Supports:

- Intrinsic Floor Analysis
- Stress and Liquidation Context
- Explainability
- AI Committee Review
- Research Reports
- Cross-Method Comparison
- Asset-Heavy Business Analysis

---

# Research Guidance

## Research Implication

Asset-based valuation outputs shall state the valuation premise and key asset adjustments so that users do not confuse accounting book value with economic asset worth.

## Examples

Examples include:

- Adjusted net asset value
- Orderly liquidation estimate
- Tangible book anchor
- Unadjusted book value presented as worth
- Real-estate NAV with third-party appraisals

## Limitations

Asset realizability can be far below carrying or appraised values under stress. Going-concern asset values may not equal liquidation proceeds.

---

# Governance

## Revision History

Version: 1.0.0

Status: Approved
Created By: DSP Research Team

## Review Notes

Initial institutional definition for REP-002.

---

# Concept Metadata

| Field | Value |
|---|---|
| Concept ID | VC-012 |
| Concept Name | Valuation Confidence |
| Category | Valuation Concept |
| Ontology Book | Book 08 — Valuation |
| Status | Approved |
| Version | 1.0.0 |
| Author | DSP Research Team |
| Reviewer | DSP Research Team |
| Approved Date | 2026-08-01 |

---

# Core Definition

## Definition

Valuation confidence is the assessed reliability of a valuation estimate, reflecting evidence strength, assumption uncertainty, method suitability, and cross-method coherence. Within DSP AI Indicator, valuation confidence is a valuation concept used to communicate how much trust should be placed in valuation outputs, applying CP-007 Confidence without redefining it.

## Purpose

Valuation confidence provides the reliability lens required to prevent false precision and to support honest explainability of valuation results.

## Why It Matters

A precise valuation number with low confidence can mislead. Correct definition binds valuation outputs to transparent confidence communication across engines, AI Committee workflows, and reports.

---

# Characteristics

## Characteristics

Valuation confidence should be:

- Explicitly labeled
- Evidence- and assumption-sensitive
- Method-aware
- Comparable across estimates only with shared criteria
- Distinct from recommendation strength
- Updateable as evidence changes

## What It Is Not

Valuation confidence is not:

- A redefinition of CP-007 Confidence
- Proof that the estimate is correct
- Market consensus
- A recommendation
- A substitute for Margin of Safety
- An investment recommendation

---

# Evidence

## Evidence Requirements

Valuation confidence assessments should be supported by:

- Evidence completeness and quality
- Assumption uncertainty notes
- Method suitability rationale
- Cross-method agreement or divergence
- Sensitivity breadth
- Known limitations and blind spots

## Confidence Drivers

Confidence increases when:

- Evidence is strong and triangulated.
- Assumptions are conservative and tested.
- Multiple methods agree.
- Sensitivities are bounded.
- Independent review corroborates coherence.

## Validation

Valuation confidence is validated through:

- Evidence-strength review
- Assumption-uncertainty checks
- Cross-method coherence tests
- Source confirmation
- Label consistency with CP-007 practice
- Separation from recommendation language

---

# Relationships

## Related Concepts

- CP-007 Confidence
- VC-001 Intrinsic Value
- VC-004 Valuation Margin of Safety
- VC-006 Discounted Cash Flow
- VC-008 Relative Valuation
- RU-012 Margin of Safety
- CP-005 Assumption

## Dependencies

Depends on:

- Book 01 — Core Principles
- VC-001 Intrinsic Value
- CP-007 Confidence

## Successor Concepts

Supports:

- Explainability
- AI Committee Review
- Research Reports
- Recommendation Caution
- Portfolio Decision Support
- Sensitivity Communication
- Trust Labeling

---

# Research Guidance

## Research Implication

Every material valuation output in DSP AI Indicator shall carry an explicit valuation confidence assessment so that users can interpret estimate reliability honestly.

## Examples

Examples include:

- High confidence when methods converge on rich evidence
- Low confidence when terminal value dominates fragile forecasts
- Medium confidence with wide scenario ranges
- Confidence omitted beneath a precise point estimate
- Confidence downgraded after contradictory evidence

## Limitations

Confidence labels remain partly judgmental. High confidence does not eliminate the possibility of large error.

---

# Governance

## Revision History

Version: 1.0.0

Status: Approved
Created By: DSP Research Team

## Review Notes

Initial institutional definition for REP-002.
