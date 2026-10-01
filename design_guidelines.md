# DSP Figma implementation guide

Visual authority: extracted ZIP at `.figma_ref/src`; preserve existing correct implementations rather than replacing the app.

## Global tokens
Use verified ZIP tokens: #080b12 background, #111520 cards, #181e2e secondary, #1e2538 borders, #dde2ed foreground, #6b7a99 muted, #7c6af7 DSP accent. The ZIP uses Fraunces headings, Inter body, and JetBrains Mono data. Earlier Inter-heading guidance was incorrect and is superseded by actual source inspection.

## App layout
220px desktop sidebar; 48px topbar; 28px content padding; 16–20px main gaps. Sidebar is viewport height with overflow support. Research CTA, real history, Buffett callout, main nav, research group, permission-filtered supplementary tools, account footer. No fake profile, history, metrics or notifications. Mobile uses existing accessible drawer and one-column content; no page overflow.

## Components
Cards: 10–14px radius, thin token borders, card background, restrained hover border. Tables: compact uppercase mono headers, 11–13px data, horizontal scroll container when necessary. Buttons: reference compact 8–10px radius, purple primary, subtle secondary, obvious disabled/focus state. Icons use existing Lucide. Charts must reflect actual API values only.

## Data states
Separate loading, empty, unavailable, forbidden and errors. Show dash for absent numbers, never zero, pseudo chart, invented signal or rating. Private provider orchestration and prompts are not client content. Index tiles without an actual index adapter must explicitly say unavailable.

## Acceptance checklist
Map all reference routes in `memory/FIGMA_PARITY.md`, compare desktop/mobile, verify navigation and forms, authenticated backend calls, genuine source provenance and preserved DSP results. A successful build is not full parity acceptance.
