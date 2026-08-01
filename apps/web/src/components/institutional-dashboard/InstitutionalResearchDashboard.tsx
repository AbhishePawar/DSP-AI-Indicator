"use client";

import { AuditPanel } from "@/components/institutional-dashboard/AuditPanel";
import { BusinessQualityPanel } from "@/components/institutional-dashboard/BusinessQualityPanel";
import { CorporateActionsPanel } from "@/components/institutional-dashboard/CorporateActionsPanel";
import { ExecutiveHeader } from "@/components/institutional-dashboard/ExecutiveHeader";
import { ExplainabilityPanel } from "@/components/institutional-dashboard/ExplainabilityPanel";
import { ExportBar } from "@/components/institutional-dashboard/ExportBar";
import { FinancialStatementsPanel } from "@/components/institutional-dashboard/FinancialStatementsPanel";
import { HistoricalSeriesPanel } from "@/components/institutional-dashboard/HistoricalSeriesPanel";
import { MarginOfSafetyPanel } from "@/components/institutional-dashboard/MarginOfSafetyPanel";
import { MarketDataPanel } from "@/components/institutional-dashboard/MarketDataPanel";
import { RiskPanel } from "@/components/institutional-dashboard/RiskPanel";
import { ScenarioPanel } from "@/components/institutional-dashboard/ScenarioPanel";
import { ValuationPanel } from "@/components/institutional-dashboard/ValuationPanel";
import { Badge } from "@/components/ui/Badge";
import type { InstitutionalDashboardView } from "@/lib/institutional-dashboard/types";

const TOC = [
  { href: "#rs-001-executive", label: "Executive" },
  { href: "#rs-002-market", label: "Market" },
  { href: "#rs-003-financial", label: "Financials" },
  { href: "#corporate-actions", label: "Corporate Actions" },
  { href: "#historical-series", label: "History" },
  { href: "#rs-005-mos", label: "Margin of Safety" },
  { href: "#rs-004-valuation", label: "Valuation" },
  { href: "#rs-006-quality", label: "Quality" },
  { href: "#rs-007-risk", label: "Risk" },
  { href: "#rs-008-scenarios", label: "Scenarios" },
  { href: "#rs-009-explainability", label: "Explainability" },
  { href: "#rs-010-audit", label: "Audit" },
] as const;

export function InstitutionalResearchDashboard({
  view,
}: {
  view: InstitutionalDashboardView;
}) {
  return (
    <div className="space-y-6">
      <nav
        aria-label="Research dashboard sections"
        className="sticky top-0 z-10 -mx-1 flex flex-wrap gap-2 border-b border-[var(--border)] bg-[var(--bg)]/95 px-1 py-2 backdrop-blur"
      >
        {TOC.map((item) => (
          <a
            key={item.href}
            href={item.href}
            className="rounded-md px-2 py-1 text-xs text-[var(--muted)] hover:bg-[var(--surface-2)] hover:text-[var(--fg)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]"
          >
            {item.label}
          </a>
        ))}
        <Badge tone="accent" className="ml-auto">
          Research Mode
        </Badge>
      </nav>

      <ExportBar view={view} />

      <ul
        className="sr-only"
        aria-label="Research Standards panel-structure check (not data completeness)"
      >
        {view.rsValidation.map((row) => (
          <li key={row.standard}>
            {row.standard}: {row.ok ? "structure present" : "structure gap"} —{" "}
            {row.detail}
          </li>
        ))}
      </ul>

      {/* Mandatory header first — MoS immediately after for prominence (RS-005) */}
      <ExecutiveHeader view={view.executive} />
      <MarginOfSafetyPanel view={view.marginOfSafety} />
      <MarketDataPanel view={view.market} />
      <FinancialStatementsPanel view={view.financial} />
      <CorporateActionsPanel view={view.corporateActions} />
      <HistoricalSeriesPanel view={view.historical} />
      <ValuationPanel view={view.valuation} />
      <BusinessQualityPanel view={view.businessQuality} />
      <RiskPanel view={view.risk} />
      <ScenarioPanel view={view.scenarios} />
      <ExplainabilityPanel scores={view.explainabilityScores} />
      <AuditPanel view={view.audit} />
    </div>
  );
}
