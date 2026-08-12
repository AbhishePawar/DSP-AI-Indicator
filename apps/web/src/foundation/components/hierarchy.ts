/**
 * EPIC-F000 — Component hierarchy (target for F001 design system).
 */

export const componentHierarchy = {
  foundations: ["tokens", "typography", "icons(lucide)", "theme"],
  primitives: [
    "Button",
    "Input",
    "Select",
    "Checkbox",
    "Dialog",
    "Tabs",
    "Table",
    "Toast",
    "Skeleton",
    "Badge",
  ],
  patterns: [
    "PageHeader",
    "EmptyState",
    "ErrorState",
    "LoadingState",
    "DataUnavailable",
    "MetricCard",
    "EvidencePanel",
  ],
  domain: [
    "ResearchSummary",
    "TrustCategoryLabel",
    "WorkflowStageChip",
    "AdminAuditTable",
  ],
  layouts: ["AppShell", "AuthShell", "AdminShell"],
  rules: [
    "F001 introduces shadcn/ui primitives aligned to PR1.2 tokens",
    "Existing components/ui remains until migrated — no parallel conflicting kits in one view",
    "Domain components stay thin — no engine logic",
  ],
} as const;
