# DSP AI Indicator — Institutional Design System

**Programme:** P9.0  
**Epic:** EPIC-001  
**Version:** 1.0.0  
**Status:** Approved (documentation foundation)  
**Owner:** DSP Design & Research Governance  
**Applies to:** Website · Dashboard · Research Workspace · Portfolio · Reports · Mobile · Admin · AI Panels  

---

## Purpose

This Design System is the **single source of truth** for visual language, interaction meaning, and UI certification across DSP AI Indicator Version 2.x.

No application surface should be redesigned until it conforms to this system.

---

## Authority & Precedence

| Layer | Role |
|---|---|
| Product Constitution | Trust → Correctness → Explainability → Consistency → A11y → Performance → Polish → Completeness |
| User Trust Standard | Every insight must be traceable, explainable, consistent, actionable, honest |
| PR1.2 VLIS (frozen) | Upstream visual operating system; this Design System **extends and packages** it for V2.x |
| REP-002 Research Ontology | Meaning of research terms; UI must not invent parallel definitions |
| **This Design System (`docs/design/`)** | Authoritative UI foundation for Version 2.x interfaces |

If implementation reveals conflict with Constitution, Trust Standard, or VLIS: **stop**, document the gap, do not silently redesign the platform.

---

## Document Index

| # | Document | Focus |
|---|---|---|
| 01 | [Brand Philosophy](01_Brand_Philosophy.md) | Institutional identity and emotional contract |
| 02 | [Brand Guidelines](02_Brand_Guidelines.md) | Voice, naming, logo, do/don’t |
| 03 | [Color System](03_Color_System.md) | Light/dark, semantic, financial, status |
| 04 | [Typography](04_Typography.md) | Hierarchy, pairing, measure |
| 05 | [Grid System](05_Grid_System.md) | Layout grids, columns, content width |
| 06 | [Spacing System](06_Spacing_System.md) | Scale, rhythm, density |
| 07 | [Iconography](07_Iconography.md) | Meaningful icons only |
| 08 | [Components](08_Components.md) | Variants: nav, cards, tables, AI panels |
| 09 | [Data Visualization](09_Data_Visualization.md) | Charts, ethics, interpretation |
| 10 | [Motion Guidelines](10_Motion_Guidelines.md) | Purposeful motion, reduced-motion |
| 11 | [Accessibility](11_Accessibility.md) | WCAG AA, trust-preserving a11y |
| 12 | [Design Tokens](12_Design_Tokens.md) | Token catalogue (light/dark) |
| 13 | [Responsive Guidelines](13_Responsive_Guidelines.md) | Breakpoints, mobile adaptation |
| 14 | [UX Principles](14_UX_Principles.md) | Four Questions, Research Mode UX |
| 15 | [UI Certification Checklist](15_UI_Certification_Checklist.md) | Gate before shipping UI |

---

## Surface Coverage

| Surface | Primary references |
|---|---|
| Website / marketing | 01, 02, 04, 10, 13 |
| Dashboard | 05, 06, 08, 09, 12 |
| Research Workspace | 03, 08, 09, 14, 15 |
| Portfolio | 03, 08, 09, 14 |
| Reports | 04, 08, 09, 11 |
| Mobile Apps | 05, 06, 11, 13 |
| Admin | 08, 11, 14 |
| AI Panels | 03, 08, 10, 14 |

---

## Non-Goals (this epic)

- Redesigning production components or pages
- Changing engines, APIs, or compliance logic
- Inventing research terminology outside REP-002
- Introducing tip-app neon, purple AI glow, or BUY/SELL chrome in Research Mode

---

## Related Upstream Docs

- `docs/PR1_2_VISUAL_LANGUAGE_AND_INTERACTION_SYSTEM.md`
- `docs/VISUAL_LANGUAGE.md`
- `docs/DESIGN_SYSTEM.md` (PR1.1 PXB summary)
- `docs/USER_TRUST_STANDARD.md`
- `docs/PRODUCT_CONSTITUTION.md`
- `docs/research/REP-002_Research_Ontology/`
