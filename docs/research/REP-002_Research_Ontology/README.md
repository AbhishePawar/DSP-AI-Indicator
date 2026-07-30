# DSP AI Indicator

## REP-002 — Research Ontology

Version: 0.1.0

Status: Draft

Owner: DSP Research Team

Governed By:
DSP Research Constitution v1.0

---

# Introduction

The DSP Research Ontology (REP-002) is the authoritative dictionary of research meaning for DSP AI Indicator. It defines the shared vocabulary through which companies, financial statements, business quality, management, economic moats, risk, valuation, prediction, portfolios, validation, and AI interpretations are named and understood.

Investment research depends on precise terminology. When two analysts, modules, or AI systems use the same word for different meanings—or different words for the same meaning—comparisons become unreliable, reports become ambiguous, and decisions lose auditability. Inconsistent definitions produce inconsistent analysis even when underlying data are identical.

REP-002 exists so that every valuation model, research report, AI explanation, recommendation surface, confidence score, and validation framework consumes one official set of meanings. It is the official language of DSP AI Indicator for research terminology and the single source of truth for concept definition within that domain.

---

# Mission

REP-002 establishes a durable institutional language for research. Its mission is to ensure that meaning remains consistent across people, modules, and time; that terminology is transparent and explainable; that analyses can be reproduced against stable definitions; that institutional knowledge is preserved rather than reinvented; and that the ontology can be maintained over a long platform lifetime without silent drift.

---

# Objectives

1. Maintain exactly one official definition per concept.
2. Eliminate ambiguity in research terminology across the platform.
3. Standardise the language used in reports, explanations, and reviews.
4. Improve AI explainability by binding interpretations to shared meanings.
5. Support validation by making concepts inspectable and comparable.
6. Preserve institutional knowledge as a governed, versioned asset.
7. Enable future contributors to extend research capabilities without inventing parallel vocabularies.

---

# Scope

## In Scope

REP-002 covers the meaning of research concepts organised across the following domains:

- Core Principles
- Company Concepts
- Financial Concepts
- Business Quality
- Management
- Economic Moat
- Risk
- Valuation
- Prediction
- Portfolio
- Validation
- AI Intelligence

Within these domains, REP-002 defines what concepts mean, how they relate at the level of meaning, and how they should be referenced consistently. It does not prescribe how systems compute outcomes.

## Out of Scope

REP-002 does not include:

- Algorithms
- Implementation design
- APIs
- Database schema
- User interface design
- Scoring logic
- Programming code

Those concerns are governed by other programme artefacts. REP-002 defines meaning, not mechanism.

---

# Guiding Principles

**One Concept = One Definition.**  
Each concept has a single official definition. Competing definitions are not permitted within the ontology.

**Evidence Before Opinion.**  
Definitions and related guidance must remain anchored to observable evidence categories and institutional research practice, not to unverified narrative preference.

**Implementation Independence.**  
Definitions must remain valid regardless of programming language, service topology, or storage technology.

**Consistency Across Modules.**  
Every module that uses a concept must consume the REP-002 definition rather than creating a local synonym or silent redefinition.

**Backward Compatibility.**  
Changes that alter established meaning require deliberate version governance. Readers of historical research must be able to identify which ontology version applied.

**Version Controlled Evolution.**  
The ontology evolves only through recorded, reviewable change. Silent edits are not acceptable.

**Human Governance.**  
Ownership, review, and approval remain human responsibilities. Automation may assist discovery; it does not replace governance.

**Long-term Stability.**  
Definitions should favour durable institutional language over temporary product wording.

---

# Ontology Structure

REP-002 is organised into twelve books. Each book is the primary home for concepts in one domain. Concepts may reference other books; they must not redefine concepts owned elsewhere.

**Book 01 — Core Principles**  
Establishes foundational research meanings that govern how all subsequent concepts are interpreted, including honesty of categories, limits of inference, and the primacy of evidence.

**Book 02 — Company Ontology**  
Defines company-level research concepts used to identify, describe, and situate an issuer within markets and competitive context.

**Book 03 — Financial Ontology**  
Defines financial-statement and financial-metric meanings used consistently across analysis, explanation, and validation.

**Book 04 — Business Quality**  
Defines concepts that describe the quality and durability of a business independent of short-term price movement.

**Book 05 — Management**  
Defines concepts related to management quality, stewardship, and related qualitative factors as used in research judgement.

**Book 06 — Economic Moat**  
Defines concepts describing durable competitive advantage and the structural conditions that sustain or erode it.

**Book 07 — Risk**  
Defines risk concepts used to name, classify, and communicate uncertainty and exposure without conflating them with valuation outputs.

**Book 08 — Valuation**  
Defines valuation concepts as meanings—what terms signify—without specifying computational methods or model code.

**Book 09 — Prediction**  
Defines prediction-related concepts, including the distinction between forecast language and verified observation.

**Book 10 — Portfolio**  
Defines portfolio-level concepts used when research moves from single-company analysis to multi-position context.

**Book 11 — Validation**  
Defines concepts that support checking, confirming, and challenging research claims against evidence and process standards.

**Book 12 — AI Intelligence**  
Defines concepts for AI-mediated interpretation so that machine-generated language remains aligned with human-governed research meaning.

Concept entries, when authored, must follow `ontology-template.md`. The catalogue of concept names belongs in `ontology-index.md` and the relevant book. This README does not define concepts.

---

# Governance

## Ownership

REP-002 is owned by the DSP Research Team. Day-to-day stewardship includes definition quality, cross-book consistency, and adherence to `RULES.md`.

## Review Process

Proposed additions or changes are submitted according to `CONTRIBUTING.md`. Reviewers assess uniqueness of definition, correct primary-book placement, template completeness, and absence of implementation content.

## Approval Process

Material changes require approval under the authority of the DSP Research Team, governed by DSP Research Constitution v1.0 (REP-001). Approval precedes publication of a new ontology version.

## Version Control

All ontology artefacts in this directory are version-controlled. The living version identifier appears in document headers. Every modification must be recorded in `CHANGELOG.md`.

## Breaking Changes

A breaking change is any change that alters the established meaning of an existing concept, removes a concept still referenced by research artefacts, or reassigns primary ownership across books in a way that invalidates prior references. Breaking changes require an explicit version increment, CHANGELOG entry, and approval under the governance process.

## Related Governance Artefacts

| Artefact | Role |
|---|---|
| `CHANGELOG.md` | Chronological record of ontology framework and content changes |
| `CONTRIBUTING.md` | Contribution, review, naming, and versioning process |
| `RULES.md` | Normative rules that all ontology work must obey |
| `DECISIONS.md` | Reserved for recorded ontology decisions (to be maintained as decisions accumulate) |

Where `DECISIONS.md` is not yet present, material decisions must still be recorded in `CHANGELOG.md` until a dedicated decisions log is established under the same governance.

---

# Versioning

REP-002 uses semantic documentation versioning for the ontology corpus.

**0.x — Draft.**  
Structure and early content may change. Definitions are provisional. Consumers should treat meanings as under formation.

**1.x — Stable.**  
Core vocabulary is approved for institutional use. Additive concepts and clarifications are preferred. Meaning-altering changes are exceptional and tightly governed.

**2.x — Major Evolution.**  
Reserved for deliberate, approved restructuring of ontology meaning or book architecture after a stable 1.x baseline. Major increments signal that prior meaning assumptions must be re-validated by consumers.

Version numbers appear in document headers and CHANGELOG entries. Status labels (for example, Draft) communicate readiness independently of the numeric version when required.

---

# Dependencies

REP-002 sits within the DSP research governance stack:

| Artefact | Relationship |
|---|---|
| **REP-001 — Research Constitution** | Superior governance. REP-002 is governed by the Constitution and must not contradict it. |
| **REP-003 — Research Methodology** | Consumes REP-002 meanings when describing how research is performed. Methodology does not redefine ontology concepts. |
| **REP-004 — Validation Standard** | Consumes REP-002 meanings when specifying how claims are validated. |
| **REP-005 — Investment Philosophy** | May reference REP-002 concepts; philosophy expresses stance, not alternate definitions. |
| **Future DSP Research Operating System** | Expected to treat REP-002 as the binding vocabulary layer for research knowledge, memory, and AI explanation surfaces. |

Downstream platform modules must align terminology to REP-002 rather than introducing independent glossaries.

---

# Future Roadmap

The following are documentation and knowledge-structure goals only. They are not implementation commitments.

1. **Concept Library** — Populate books with approved concept entries using the ontology template.
2. **Cross References** — Formalise bidirectional references between related concepts across books.
3. **Ontology Graph** — Represent concept relationships for navigation and consistency checks.
4. **Knowledge Graph Integration** — Align future knowledge representations with REP-002 identifiers and meanings.
5. **Research Memory** — Preserve historical concept versions alongside research artefacts that depended on them.
6. **AI Knowledge Layer** — Require AI explanations to cite ontology concepts rather than inventing parallel language.
7. **Validation Links** — Connect validation standards (REP-004) to named ontology concepts.
8. **Future Books** — Add books only through governance when a domain cannot be housed without ambiguity in the existing twelve.

---

# Conclusion

REP-002 is the official research language of DSP AI Indicator. It exists to make research meaning consistent, transparent, explainable, and durable across the platform’s lifetime.

Every future research capability—human or automated—must align with this ontology. Where a required meaning does not yet exist, it must be added to REP-002 through governance rather than invented locally. Meaning is institutional property; REP-002 is its register.
