# Information Architecture

**Epic:** PR1.1 · Product Experience Blueprint  
**Nav source (implemented):** `apps/web` primary nav · future routes marked *planned*

---

## 1. Site map

```text
DSP AI Indicator
├── /login
├── /dashboard                          [L1.1]
├── /analysis                           [L1.1 stub → L1.2 full]
├── /compare                            [L1.1 stub → L1.6+]
├── /portfolio                          [L1.1 stub → L1.4]
├── /copilot                            [L1.1 stub → L1.3]
├── /reports                            [L1.1]
│   └── /reports/[id]
├── /settings                           [L1.1]
├── /health · /platform                 [ops / diagnostics]
├── /advisor/*                          [FUTURE — SEBI / advisor]
└── /portal/*                           [FUTURE — client portal]
```

Mobile shares the same routes; presentation differs ([MOBILE_UX.md](MOBILE_UX.md)).

---

## 2. Screen definitions

### 2.1 Dashboard

| | |
|---|---|
| **Purpose** | Central entry; answer “where do I start?” |
| **Primary jobs** | Quick actions, health pulse, search, recent reports, copilot entry |
| **Widgets** | Quick Actions, Platform Health, Platform Info, Company Search, AI Copilot Card, Favorites (placeholder), Recent Reports, Recent Activity (placeholder) |
| **Four Q** | Status of platform · why research-ready · why start here · next = Analyze / Copilot |
| **Flags** | Research Mode banner when research-only |

### 2.2 Company Analysis

| | |
|---|---|
| **Purpose** | Understand one business end-to-end |
| **Order** | Frozen in [PRODUCT_EXPERIENCE_BLUEPRINT.md](PRODUCT_EXPERIENCE_BLUEPRINT.md) §4 |
| **Chrome** | Section TOC (desktop), accordion (mobile), Copilot rail/sheet |
| **Exit** | Export · save report id · open Copilot · Compare peers |

### 2.3 Compare Companies

| | |
|---|---|
| **Purpose** | Peer relative view via API envelopes |
| **IA blocks** | Peer picker · comparison matrix · relative strengths · risks · Copilot |
| **Non-goal** | Client-side scoring |

### 2.4 Portfolio

| | |
|---|---|
| **Purpose** | Holdings overview citing backend portfolio artifacts |
| **IA blocks** | Summary · holdings table · concentration · drill-to-analysis · alerts (flag-gated) |
| **Research Mode** | No Buy/Sell on positions |

### 2.5 AI Copilot

| | |
|---|---|
| **Purpose** | Natural-language explanation over cited context |
| **Modes** | Full page + contextual drawer/sheet from Analysis |
| **See** | [AI_COPILOT_UX.md](AI_COPILOT_UX.md) |

### 2.6 Reports

| | |
|---|---|
| **Purpose** | Retrieve prior API report envelopes |
| **IA** | List (local recent ids) · detail JSON/structured view · Evidence link · Export |

### 2.7 Settings

| | |
|---|---|
| **Purpose** | Theme (light/dark/system), session, disclaimer preference display |
| **Non-goal** | Trading preferences / tip frequency |

### 2.8 Advisor (future)

| | |
|---|---|
| **Audience** | Registered advisors (SEBI Mode) |
| **IA sketch** | Client list · model portfolios · recommendation history · disclosures · audit |
| **Gate** | `SEBI_MODE` + role |

### 2.9 Client Portal (future)

| | |
|---|---|
| **Audience** | End clients of advisors |
| **IA sketch** | Shared reports · plain-language summaries · disclaimers · Q&A via Copilot |
| **Gate** | SEBI + portal feature (future flag) |

### 2.10 Mobile

Same IA nodes; navigation via drawer; Analysis as stacked accordions; Copilot as bottom sheet. See [MOBILE_UX.md](MOBILE_UX.md).

---

## 3. Global navigation

| Item | Route | Phase |
|---|---|---|
| Dashboard | `/dashboard` | L1.1 |
| Company Analysis | `/analysis` | L1.2 |
| Compare Companies | `/compare` | L1.6+ |
| Portfolio | `/portfolio` | L1.4 |
| AI Copilot | `/copilot` | L1.3 |
| Reports | `/reports` | L1.5 |
| Settings | `/settings` | L1.1 |
| Logout | action | L1.1 |
| Advisor | `/advisor` | Future |
| Client Portal | `/portal` | Future |

---

## 4. Cross-links

```text
Dashboard ──► Analysis, Compare, Copilot, Reports
Analysis ──► Copilot, Compare (peers), Reports (save), Export
Portfolio ──► Analysis (per symbol)
Reports ──► Analysis (re-open symbol if known)
Copilot ──► Analysis section anchors
```

---

## 5. Content hierarchy rules

1. **Brand / product** visible in shell  
2. **Research Conclusion** before deep metrics  
3. **Decision Dashboard** after evidence-building sections (summary of scores)  
4. **Evidence / Export** last  
5. Diagnostics (`/health`, `/platform`) secondary — linked from widgets, not primary nav  

---

## 6. Accessibility IA

- Skip link → `#main-content`  
- Landmarks: `nav`, `main`, `complementary` (TOC / Copilot)  
- Breadcrumbs for depth > 1  
- Section headings `h2` per analysis block  
