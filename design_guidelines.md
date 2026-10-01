# DSP Figma implementation guide

Visual authority: extracted ZIP at `.figma_ref/src`; preserve existing correct implementations rather than replacing the app.

## Global tokens
Use `globals.css` mappings to reference `index.css`: dark #0c0c0e background, #131315 cards, #1c1c20 secondary, #232328 borders, #fafafa foreground, #72727e muted, #7c6af7 DSP accent. Reference uses Inter for headings/body and JetBrains Mono for data. The user explicitly selected this design; do not substitute unrelated fonts or palettes.

## App layout
220px desktop sidebar; 48px topbar; 28px content padding; 16–20px main gaps. Sidebar is viewport height with overflow support. Research CTA, real history, Buffett callout, main nav, research group, permission-filtered supplementary tools, account footer. No fake profile, history, metrics or notifications. Mobile uses existing accessible drawer and one-column content; no page overflow.

## Components
Cards: 10–14px radius, thin token borders, card background, restrained hover border. Tables: compact uppercase mono headers, 11–13px data, horizontal scroll container when necessary. Buttons: reference compact 8–10px radius, purple primary, subtle secondary, obvious disabled/focus state. Icons use existing Lucide. Charts must reflect actual API values only.

## Data states
Separate loading, empty, unavailable, forbidden and errors. Show dash for absent numbers, never zero, pseudo chart, invented signal or rating. Private provider orchestration and prompts are not client content. Index tiles without an actual index adapter must explicitly say unavailable.

## Acceptance checklist
Map all reference routes in `memory/FIGMA_PARITY.md`, compare desktop/mobile, verify navigation and forms, authenticated backend calls, genuine source provenance and preserved DSP results. A successful build is not full parity acceptance.
