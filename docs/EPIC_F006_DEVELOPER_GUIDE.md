# EPIC-F006 — Developer Guide

## Entry

```tsx
import { PortfolioIntelligenceWorkspace } from "@/components/portfolio-intelligence";
```

Route: `/portfolio` · optional `?section=holdings`

## Preferences

```ts
import { usePortfolioIntelPrefsStore } from "@/lib/portfolio-intelligence";
```

## Keyboard

| Shortcut | Action |
|---|---|
| 1–7 | Jump section |
| `[` / `]` | Toggle left / right panels |

## Tests

```bash
cd apps/web && npm test -- src/lib/portfolio-intelligence/portfolio-intelligence.test.tsx
```

## Do not

- Call client allocation / risk / CAGR helpers as product metrics
- Add portfolio backend endpoints in this epic
- Change F005 Company Analysis Workspace
