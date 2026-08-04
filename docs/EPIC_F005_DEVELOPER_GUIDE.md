# EPIC-F005 — Developer Guide

## Entry

```tsx
import { CompanyAnalysisWorkspace } from "@/components/company-analysis";
```

Route: `apps/web/src/app/analysis/page.tsx` · URL: `/analysis?symbol=AAPL`

## Preferences

```ts
import { useWorkspacePrefsStore } from "@/lib/company-analysis";
useWorkspacePrefsStore.getState().setActiveSection("valuation");
```

Pins / recent searches reuse `useDashboardPrefsStore` from F004.

## Keyboard

| Shortcut | Action |
|---|---|
| Ctrl/⌘ + Enter | Run analysis |
| 1–8 | Jump section |
| `[` / `]` | Toggle left / right panels |

## Tests

```bash
cd apps/web && npm test -- src/lib/company-analysis/company-analysis.test.tsx
```

## Do not

- Add backend endpoints
- Calculate valuation / scores in the browser
- Bypass F001 for new chrome
- Fabricate committee or compliance outcomes
