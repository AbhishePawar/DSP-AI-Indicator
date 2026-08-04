# EPIC-F004 — Developer Guide

## Entry

```tsx
import { InstitutionalDashboard } from "@/components/dashboard";
```

Route: `apps/web/src/app/dashboard/page.tsx`

## Preferences

```ts
import { useDashboardPrefsStore } from "@/lib/dashboard";

useDashboardPrefsStore.getState().toggleWidgetVisible("background_jobs");
useDashboardPrefsStore.getState().pinCompany("AAPL");
```

## Adding a widget

1. Add id + meta to `widgetRegistry.ts`
2. Implement component under `components/dashboard/widgets/`
3. Wire in `InstitutionalDashboard` `renderWidget`
4. Keep F001 imports only; consume existing `api` / `rbacAuthApi` or empty state

## Tests

```bash
cd apps/web && npm test -- src/lib/dashboard/dashboard.test.tsx
```

## Do not

- Add backend endpoints
- Fabricate business metrics
- Bypass the F003 shell
- Import legacy `@/components/ui` for new dashboard chrome
