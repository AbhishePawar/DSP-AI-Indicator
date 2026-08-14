/**
 * EPIC-F000 — Approved technology decisions (frozen).
 */

export const technologyDecisions = {
  framework: { choice: "Next.js 15 App Router", reason: "SSR/RSC + institutional routing" },
  language: { choice: "TypeScript strict", reason: "Contract safety with /api/v1" },
  styling: { choice: "Tailwind CSS 4", reason: "Utility-first; tokenized via CSS vars" },
  ui: {
    choice: "shadcn/ui primitives (@/components/ds)",
    reason: "Accessible Radix primitives mapped to PR1.2 tokens",
    interim: "components/ui legacy kit coexists until page migration",
  },
  icons: { choice: "lucide-react", reason: "Consistent stroke icons" },
  clientState: {
    choice: "zustand (F002+ page wiring)",
    reason: "Approved in F000; adopt with application experiences",
  },
  serverState: { choice: "@tanstack/react-query", reason: "Already in production" },
  forms: {
    choice: "DS FormField + RHF/Zod in F002+",
    reason: "Primitives ready; form libs wire with auth experience",
  },
  tables: { choice: "@tanstack/react-table via DataGrid", reason: "Headless enterprise tables" },
  charts: {
    choice: "Apache ECharts shells (no financial charts yet)",
    reason: "Container/theme/responsive wrappers only in F001",
  },
  theme: {
    choice: "ThemeProvider + next-themes DspThemeProvider",
    reason: "System/light/dark with data-theme CSS vars",
  },
  auth: { choice: "JWT via backend /auth*", reason: "No client-side identity invent" },
  testing: { choice: "Vitest + Testing Library", reason: "Already configured" },
  lintFormat: { choice: "ESLint + Prettier", reason: "F000 baseline" },
  storybook: { choice: "optional / deferred", reason: "Catalogue docs suffice for F001" },
} as const;
