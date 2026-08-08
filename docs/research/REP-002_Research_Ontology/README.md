# DSP AI Indicator

## REP-002 — Research Ontology

Version: 1.0.0

Status: Approved

Owner: DSP Research Team

Governed By:
DSP Research Constitution v1.0

---

# Introduction

The DSP Research Ontology (REP-002) is the authoritative dictionary of research meaning for DSP AI Indicator. It defines the shared vocabulary through which research objects, financial statements, business quality, management, economic moats, risk, valuation, decision framework outcomes, and governance / AI intelligence presentation are named and understood.

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

## In Scope (Version 1.0.0)

REP-002 Version 1.0.0 covers the meaning of research concepts organised across the following approved books:

- Book 01 — Core Principles
- Book 02 — Research Objects
- Book 03 — Financial Ontology
- Book 04 — Business Quality
- Book 05 — Management
- Book 06 — Economic Moat
- Book 07 — Risk
- Book 08 — Valuation
- Book 09 — Decision Framework
- Book 10 — Governance & AI Intelligence

Within these domains, REP-002 defines what concepts mean, how they relate at the level of meaning, and how they should be referenced consistently. It does not prescribe how systems compute outcomes.

## Out of Scope (Version 1.0.0)

REP-002 Version 1.0.0 does not include:

- Algorithms
- Implementation design
- APIs
- Database schema
- User interface design
- Scoring logic
- Programming code
- A dedicated Portfolio ontology book
- A dedicated Prediction ontology book
- A dedicated Validation ontology book separate from Governance
- A dedicated Company Ontology book separate from Research Objects
- A dedicated AI Intelligence book separate from Book 10

Those product or future-book concerns are governed by other programme artefacts or by post–v1.0 ontology governance. REP-002 defines meaning, not mechanism.

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

REP-002 Version 1.0.0 is organised into **ten** approved books. Each book is the primary home for concepts in one domain. Concepts may reference other books; they must not redefine concepts owned elsewhere.

**Book 01 — Core Principles**  
Foundational research meanings: Truth, Evidence, Fact, Observation, Assumption, Inference, and Confidence.

**Book 02 — Research Objects**  
Identity and artefact objects: Entity, Organization, Security, Financial Statement, Metric, Dataset, Source, Document, Time Period, and Currency.

**Book 03 — Financial Ontology**  
Financial-statement and financial-metric meanings used across analysis, explanation, and validation.

**Book 04 — Business Quality**  
Concepts describing business quality and durability independent of short-term price movement.

**Book 05 — Management**  
Management quality, integrity, governance, incentives, stewardship, and related qualitative factors.

**Book 06 — Economic Moat**  
Durable competitive advantage and the conditions that sustain or erode it.

**Book 07 — Risk**  
Risk concepts used to name exposure and uncertainty without conflating them with valuation outputs.

**Book 08 — Valuation**  
Valuation meanings—what terms signify—without specifying computational methods or model code.

**Book 09 — Decision Framework**  
Integration layer combining prior domains into research conclusions, theses, decision confidence, recommendation states, review, revision, lifecycle, and learning. May depend on Book 10 for governance presentation concepts.

**Book 10 — Governance & AI Intelligence**  
AI committee, explainability, recommendation presentation, analytical confidence, policy, transparency, traceability, auditability, decision records, validation rules, and human oversight.

Concept entries follow `ontology-template.md` (Version 2 / Variant 2a). The catalogue of concept names belongs in `ontology-index.md`, `CONCEPT_ID_REGISTRY.md`, and the relevant book. This README does not define concepts.

### Deprecated placeholder filenames

The following filenames, if present, are **not** v1.0 concept homes. They are deprecated stubs only:

- `Book_02_Company_Ontology.md` → use Book 02 — Research Objects
- `Book_09_Prediction.md` → out of v1.0; constrained by Core Principles and Decision Framework
- `Book_10_Portfolio.md` → out of v1.0; Portfolio ontology is a post–v1.0 candidate
- `Book_11_Validation.md` → use Book 10 governance validation concepts
- `Book_12_AI_Intelligence.md` → merged into Book 10 — Governance & AI Intelligence

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
| `CONCEPT_ID_REGISTRY.md` | Authoritative concept ID catalogue |
| `ONTOLOGY_ROADMAP.md` | Approved book architecture and completion map |
| `ontology-index.md` | Navigational catalogue of concept names |
| `REP_002_v1_CERTIFICATION_REPORT.md` | Version 1.0 institutional certification record |
| `DECISIONS.md` | Reserved for recorded ontology decisions (to be maintained as decisions accumulate) |

Where `DECISIONS.md` is not yet present, material decisions must still be recorded in `CHANGELOG.md` until a dedicated decisions log is established under the same governance.

---

# Versioning

REP-002 uses semantic documentation versioning for the ontology corpus.

**0.x — Draft.**  
Structure and early content may change. Definitions are provisional.

**1.x — Stable.**  
Core vocabulary is approved for institutional use. Additive concepts and clarifications are preferred. Meaning-altering changes are exceptional and tightly governed.

**2.x — Major Evolution.**  
Reserved for deliberate, approved restructuring of ontology meaning or book architecture after a stable 1.x baseline.

**Current corpus version: 1.0.0 (Approved).**

Version numbers appear in document headers and CHANGELOG entries. Status labels communicate readiness independently of the numeric version when required.

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

1. **Cross References** — Maintain bidirectional references between related concepts across books.
2. **Ontology Graph** — Represent concept relationships for navigation and consistency checks.
3. **Knowledge Graph Integration** — Align future knowledge representations with REP-002 identifiers and meanings.
4. **Research Memory** — Preserve historical concept versions alongside research artefacts that depended on them.
5. **AI Knowledge Layer** — Require AI explanations to cite ontology concepts rather than inventing parallel language.
6. **Validation Links** — Connect validation standards (REP-004) to named ontology concepts.
7. **Post–v1.0 Books** — Portfolio (and any other domain) only through governance when a domain cannot be housed without ambiguity in the existing ten books.

---

# Conclusion

REP-002 Version 1.0.0 is the official research language of DSP AI Indicator. It exists to make research meaning consistent, transparent, explainable, and durable across the platform’s lifetime.

Every future research capability—human or automated—must align with this ontology. Where a required meaning does not yet exist, it must be added to REP-002 through governance rather than invented locally. Meaning is institutional property; REP-002 is its register.
