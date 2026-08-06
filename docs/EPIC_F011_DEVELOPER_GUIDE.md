# EPIC-F011 — Developer Guide

## Run E2E journey suite

```bash
cd apps/web
npm run test:e2e
```

## Coverage module

```ts
import { E2E_JOURNEYS, E2E_CRITICAL_ROUTES } from "@/e2e";
```

## Do not

- Add product features while “fixing”
- Change backend or API contracts
- Invent client business logic to make tests pass
