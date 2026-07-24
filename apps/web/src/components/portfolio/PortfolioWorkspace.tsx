"use client";

import { memo, useMemo, useState } from "react";

import {
  AllocationDonut,
  ExpectedReturnChart,
  PortfolioEmptyState,
  PortfolioRiskHeatmap,
  QualityHistogram,
  SectorBarChart,
  TrustedMetricBlock,
  WeightTreemap,
} from "@/components/portfolio/PortfolioVisuals";
import { ConfidenceBadge } from "@/components/trust/ConfidenceBadge";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card, CardBody, CardHeader } from "@/components/ui/Card";
import { EXPORT_FORMATS, type ExportFormatId } from "@/lib/analysis/sprint7Reports";
import {
  exportPortfolioReport,
  type PortfolioReportKind,
} from "@/lib/portfolio/portfolioReports";
import {
  PORTFOLIO_TOC,
  type PortfolioHolding,
  type PortfolioWorkspaceView,
  type RebalanceSuggestion,
  type ScenarioRow,
  type WatchlistItem,
} from "@/lib/portfolio/portfolioWorkspace";

export const PortfolioOverviewCard = memo(function PortfolioOverviewCard({
  view,
}: {
  view: PortfolioWorkspaceView;
}) {
  const m = view.overview;
  return (
    <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
      <TrustedMetricBlock metric={m.portfolioValue} />
      <TrustedMetricBlock metric={m.cashPercent} />
      <TrustedMetricBlock metric={m.investedPercent} />
      <TrustedMetricBlock metric={m.averageMos} />
      <TrustedMetricBlock metric={m.expectedCagr} />
      <TrustedMetricBlock metric={m.portfolioRiskScore} />
      <TrustedMetricBlock metric={m.concentrationScore} />
      <TrustedMetricBlock metric={m.diversificationScore} />
      <TrustedMetricBlock metric={view.cash} />
    </div>
  );
});

export const PortfolioHoldingCard = memo(function PortfolioHoldingCard({
  holding,
}: {
  holding: PortfolioHolding;
}) {
  return (
    <Card>
      <CardHeader
        title={`${holding.symbol} · ${holding.name}`}
        action={<ConfidenceBadge level={holding.confidence} />}
      />
      <CardBody className="grid gap-2 text-sm sm:grid-cols-2">
        <Field label="Weight" value={holding.weight != null ? `${holding.weight.toFixed(1)}%` : null} />
        <Field label="Market value" value={holding.marketValue?.toLocaleString() ?? null} />
        <Field label="Purchase / Current" value={`${holding.purchasePrice ?? "—"} / ${holding.currentPrice ?? "—"}`} />
        <Field label="Target allocation" value={holding.targetAllocation != null ? `${holding.targetAllocation}%` : null} />
        <Field label="Intrinsic value" value={holding.intrinsicValue?.toLocaleString() ?? null} />
        <Field label="MOS" value={holding.marginOfSafety != null ? `${holding.marginOfSafety.toFixed(1)}%` : null} />
        <Field label="Expected CAGR" value={holding.expectedCagr != null ? `${holding.expectedCagr}%` : null} />
        <Field label="Sector / Industry" value={`${holding.sector} / ${holding.industry}`} />
        <Field label="Quality / Moat / Risk" value={`${holding.businessQuality ?? "Unavailable"} / ${holding.moatRating ?? "Unavailable"} / ${holding.riskRating ?? "Unavailable"}`} />
        <Field label="Evidence" value={holding.evidence} />
        <Field label="Methodology" value={holding.methodology} />
        <Field label="Updated" value={holding.lastUpdated} />
      </CardBody>
    </Card>
  );
});

function Field({ label, value }: { label: string; value: string | null | undefined }) {
  return (
    <div>
      <p className="text-xs font-medium uppercase tracking-wide text-[var(--muted)]">{label}</p>
      <p className="mt-0.5">{value ?? "Unavailable"}</p>
    </div>
  );
}

export function PortfolioAllocationChart({ view }: { view: PortfolioWorkspaceView }) {
  return <AllocationDonut slices={view.allocations.sector} title="Sector allocation" />;
}

export function PortfolioSectorChart({ view }: { view: PortfolioWorkspaceView }) {
  return <SectorBarChart slices={view.allocations.sector} title="Sector bar" />;
}

export function PortfolioPerformanceCard({ view }: { view: PortfolioWorkspaceView }) {
  return (
    <Card>
      <CardHeader title="Performance context" description="Presentation metrics — not a live P&amp;L engine" />
      <CardBody className="grid gap-3 sm:grid-cols-2">
        <TrustedMetricBlock metric={view.overview.expectedUpside} />
        <TrustedMetricBlock metric={view.overview.downsideRisk} />
        <TrustedMetricBlock metric={view.overview.averageIntrinsicDiscount} />
        <TrustedMetricBlock metric={view.overview.averageQuality} />
      </CardBody>
    </Card>
  );
}

export function PortfolioWatchlistCard({ item }: { item: WatchlistItem }) {
  return (
    <Card>
      <CardHeader title={item.symbol} action={<ConfidenceBadge level={item.confidence} />} />
      <CardBody className="space-y-2 text-sm">
        <p className="font-medium">{item.name}</p>
        <Field label="Target buy price" value={item.targetBuyPrice?.toLocaleString() ?? null} />
        <Field label="Current price" value={item.currentPrice?.toLocaleString() ?? null} />
        <Field label="Current discount" value={item.currentDiscount != null ? `${item.currentDiscount.toFixed(1)}%` : null} />
        <Field label="MOS" value={item.marginOfSafety != null ? `${item.marginOfSafety}%` : null} />
        <Field label="Intrinsic value" value={item.intrinsicValue?.toLocaleString() ?? null} />
        <Field label="Expected CAGR" value={item.expectedCagr != null ? `${item.expectedCagr}%` : null} />
        <Field label="Reason to watch" value={item.reasonToWatch} />
        <Field label="Alert" value={item.alertPlaceholder} />
        <Field label="Evidence" value={item.evidence} />
        <Field label="Methodology" value={item.methodology} />
      </CardBody>
    </Card>
  );
}

export function PortfolioOpportunityCard({ view }: { view: PortfolioWorkspaceView }) {
  return (
    <Card>
      <CardHeader title="Top opportunities" />
      <CardBody>
        <ol className="list-decimal space-y-1 pl-5 text-sm">
          {view.risk.topOpportunities.map((o) => (
            <li key={o}>{o}</li>
          ))}
        </ol>
      </CardBody>
    </Card>
  );
}

export function PortfolioValuationSummary({ view }: { view: PortfolioWorkspaceView }) {
  return (
    <div className="grid gap-3 sm:grid-cols-2">
      <TrustedMetricBlock metric={view.expectedReturn.portfolioFairValue} />
      <TrustedMetricBlock metric={view.expectedReturn.portfolioIntrinsicValue} />
      <TrustedMetricBlock metric={view.overview.averageMos} />
      <TrustedMetricBlock metric={view.overview.weightedRoce} />
      <TrustedMetricBlock metric={view.overview.weightedRoe} />
    </div>
  );
}

export function PortfolioMoatDistribution({ view }: { view: PortfolioWorkspaceView }) {
  return <QualityHistogram slices={view.moatDistribution} title="Moat distribution" />;
}

export function PortfolioQualityDistribution({ view }: { view: PortfolioWorkspaceView }) {
  return <QualityHistogram slices={view.qualityDistribution} title="Quality distribution" />;
}

export function PortfolioDiversificationCard({ view }: { view: PortfolioWorkspaceView }) {
  return (
    <Card>
      <CardHeader title="Diversification" />
      <CardBody className="grid gap-3 sm:grid-cols-2">
        <TrustedMetricBlock metric={view.overview.diversificationScore} />
        <TrustedMetricBlock metric={view.overview.concentrationScore} />
        <TrustedMetricBlock metric={view.risk.largestPosition} />
        <TrustedMetricBlock metric={view.risk.largestSector} />
      </CardBody>
    </Card>
  );
}

export function PortfolioRebalanceSuggestions({
  items,
}: {
  items: RebalanceSuggestion[];
}) {
  return (
    <Card>
      <CardHeader
        title="Rebalance suggestions"
        description="Educational only — no automatic trading"
      />
      <CardBody className="space-y-3">
        {items.map((r) => (
          <div key={r.id} className="rounded-md border border-[var(--border)] p-3 text-sm">
            <div className="flex flex-wrap items-center gap-2">
              <span className="font-medium">{r.symbol}</span>
              <Badge tone="accent">{r.action.replace(/_/g, " ")}</Badge>
              <ConfidenceBadge level={r.confidence} />
            </div>
            <p className="mt-1">{r.rationale}</p>
            <p className="mt-1 text-xs text-[var(--muted)]">Evidence: {r.evidence}</p>
          </div>
        ))}
      </CardBody>
    </Card>
  );
}

export function PortfolioScenarioAnalysis({ rows }: { rows: ScenarioRow[] }) {
  return (
    <Card>
      <CardHeader title="Scenario analysis" description="Qualitative overlays — not forecasts" />
      <CardBody className="space-y-3">
        {rows.map((s) => (
          <div key={s.id} className="rounded-md border border-[var(--border)] p-3 text-sm">
            <div className="flex flex-wrap items-center gap-2">
              <span className="font-medium">{s.label}</span>
              <ConfidenceBadge level={s.confidence} />
            </div>
            <p className="mt-1">{s.portfolioImpact}</p>
            <p className="text-xs text-[var(--muted)]">
              Return delta: {s.expectedReturnDelta ?? "Unavailable"}
              <br />
              Evidence: {s.evidence} · {s.methodology}
            </p>
          </div>
        ))}
      </CardBody>
    </Card>
  );
}

export function PortfolioExpectedReturn({ view }: { view: PortfolioWorkspaceView }) {
  return (
    <div className="space-y-4">
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
        <TrustedMetricBlock metric={view.expectedReturn.expectedCagr} />
        <TrustedMetricBlock metric={view.expectedReturn.expectedDividendYield} />
        <TrustedMetricBlock metric={view.expectedReturn.expectedTotalReturn} />
      </div>
      <ExpectedReturnChart
        cagr={view.expectedReturn.expectedCagr}
        total={view.expectedReturn.expectedTotalReturn}
      />
    </div>
  );
}

export function PortfolioRiskMetrics({ view }: { view: PortfolioWorkspaceView }) {
  const scores = view.holdings.map((h) => h.weight ?? 0);
  return (
    <div className="space-y-4">
      <div className="grid gap-3 sm:grid-cols-2">
        <TrustedMetricBlock metric={view.risk.largestPosition} />
        <TrustedMetricBlock metric={view.risk.largestSector} />
        <TrustedMetricBlock metric={view.risk.largestDrawdownRisk} />
        <TrustedMetricBlock metric={view.overview.portfolioRiskScore} />
      </div>
      <PortfolioRiskHeatmap
        symbols={view.holdings.map((h) => h.symbol)}
        scores={scores}
      />
      <Card>
        <CardHeader title="Risk lists" />
        <CardBody className="grid gap-3 text-sm sm:grid-cols-2">
          <List label="Top risks" items={view.risk.topRisks} />
          <List label="Overvalued" items={view.risk.overvaluedHoldings} />
          <List label="Undervalued" items={view.risk.undervaluedHoldings} />
          <List label="High debt / high risk" items={view.risk.highDebtHoldings} />
          <List label="Low confidence" items={view.risk.lowConfidenceHoldings} />
        </CardBody>
      </Card>
    </div>
  );
}

function List({ label, items }: { label: string; items: string[] }) {
  return (
    <div>
      <p className="text-xs font-medium uppercase text-[var(--muted)]">{label}</p>
      <ul className="mt-1 list-disc pl-5">
        {(items.length ? items : ["None listed"]).map((i) => (
          <li key={i}>{i}</li>
        ))}
      </ul>
    </div>
  );
}

export function PortfolioCashAllocation({ view }: { view: PortfolioWorkspaceView }) {
  return (
    <div className="grid gap-3 sm:grid-cols-2">
      <TrustedMetricBlock metric={view.cash} />
      <TrustedMetricBlock metric={view.overview.cashPercent} />
      <TrustedMetricBlock metric={view.overview.investedPercent} />
    </div>
  );
}

export function PortfolioNotes({ notes, disclosures }: { notes: string[]; disclosures: string[] }) {
  return (
    <Card>
      <CardHeader title="Notes & disclosures" />
      <CardBody className="space-y-3 text-sm">
        <List label="Notes" items={notes} />
        <List label="Disclosures" items={disclosures} />
      </CardBody>
    </Card>
  );
}

function HoldingsTable({ holdings }: { holdings: PortfolioHolding[] }) {
  const [visible, setVisible] = useState(20);
  const rows = holdings.slice(0, visible);
  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[40rem] text-left text-sm">
        <caption className="sr-only">Portfolio holdings</caption>
        <thead>
          <tr className="border-b border-[var(--border)] text-[var(--muted)]">
            <th className="px-2 py-2" scope="col">Symbol</th>
            <th className="px-2 py-2" scope="col">Weight</th>
            <th className="px-2 py-2" scope="col">MOS</th>
            <th className="px-2 py-2" scope="col">Confidence</th>
            <th className="px-2 py-2" scope="col">Sector</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((h) => (
            <tr key={h.id} className="border-b border-[var(--border)]">
              <td className="px-2 py-2 font-medium">{h.symbol}</td>
              <td className="px-2 py-2">{h.weight?.toFixed(1) ?? "Unavailable"}%</td>
              <td className="px-2 py-2">
                {h.marginOfSafety != null ? `${h.marginOfSafety.toFixed(1)}%` : "Unavailable"}
              </td>
              <td className="px-2 py-2">
                <ConfidenceBadge level={h.confidence} />
              </td>
              <td className="px-2 py-2">{h.sector}</td>
            </tr>
          ))}
        </tbody>
      </table>
      {holdings.length > visible ? (
        <Button
          variant="ghost"
          size="sm"
          className="mt-2"
          onClick={() => setVisible((v) => v + 20)}
        >
          Show more
        </Button>
      ) : null}
    </div>
  );
}

export function PortfolioExportPanel({ view }: { view: PortfolioWorkspaceView }) {
  const [format, setFormat] = useState<ExportFormatId>("markdown");
  const [msg, setMsg] = useState<string | null>(null);
  const kinds: { id: PortfolioReportKind; label: string }[] = [
    { id: "portfolio_report", label: "Portfolio Report" },
    { id: "allocation_report", label: "Allocation Report" },
    { id: "risk_report", label: "Risk Report" },
    { id: "watchlist_report", label: "Watchlist Report" },
  ];

  const onExport = (kind: PortfolioReportKind) => {
    const res = exportPortfolioReport(view, kind, format);
    setMsg(
      res.ok
        ? `Exported ${kind} as ${format}`
        : res.reason,
    );
  };

  return (
    <Card id="pf_export">
      <CardHeader
        title="Export (Sprint 7 pipeline)"
        description="Markdown / HTML / JSON / CSV client-side · PDF/DOCX placeholders"
      />
      <CardBody className="space-y-3">
        <label className="block text-sm">
          Format
          <select
            className="mt-1 min-h-11 w-full rounded-md border border-[var(--border)] bg-[var(--surface)] px-2"
            value={format}
            onChange={(e) => setFormat(e.target.value as ExportFormatId)}
          >
            {EXPORT_FORMATS.map((f) => (
              <option key={f.id} value={f.id}>
                {f.label}
                {f.ready ? "" : " (placeholder)"}
              </option>
            ))}
          </select>
        </label>
        <div className="flex flex-wrap gap-2">
          {kinds.map((k) => (
            <Button key={k.id} variant="secondary" onClick={() => onExport(k.id)}>
              {k.label}
            </Button>
          ))}
        </div>
        {msg ? <p className="text-sm text-[var(--muted)]" role="status">{msg}</p> : null}
      </CardBody>
    </Card>
  );
}

export const PortfolioWorkspace = memo(function PortfolioWorkspace({
  view,
}: {
  view: PortfolioWorkspaceView;
}) {
  const sticky = useMemo(
    () => ({
      value: view.overview.portfolioValue.value ?? "Unavailable",
      cash: view.overview.cashPercent.value ?? "Unavailable",
      risk: view.overview.portfolioRiskScore.value ?? "Unavailable",
    }),
    [view],
  );

  if (view.empty) {
    return <PortfolioEmptyState />;
  }

  return (
    <div className="relative pb-24 md:pb-8">
      <div className="sticky top-14 z-20 mb-4 space-y-1 border-b border-[var(--border)] bg-[var(--surface)]/95 p-3 backdrop-blur lg:top-16">
        <p className="text-xs text-[var(--muted)]">Portfolio summary · {view.version}</p>
        <p className="font-medium">
          Value {sticky.value} · Cash {sticky.cash} · Risk {sticky.risk}
        </p>
        <nav className="flex flex-wrap gap-3 text-xs" aria-label="Portfolio sections">
          {PORTFOLIO_TOC.map((t) => (
            <a key={t.id} href={`#${t.id}`} className="text-[var(--accent)] underline">
              {t.title}
            </a>
          ))}
        </nav>
      </div>

      <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_18rem]">
        <div className="min-w-0 space-y-8">
          <section id="pf_overview" className="scroll-mt-28 space-y-4">
            <h2 className="font-[family-name:var(--font-display)] text-2xl">Overview</h2>
            <PortfolioOverviewCard view={view} />
            <PortfolioPerformanceCard view={view} />
            <PortfolioCashAllocation view={view} />
          </section>

          <section id="pf_holdings" className="scroll-mt-28 space-y-4">
            <h2 className="font-[family-name:var(--font-display)] text-2xl">Holdings</h2>
            <Card>
              <CardHeader title="Holdings table" />
              <CardBody>
                <HoldingsTable holdings={view.holdings} />
              </CardBody>
            </Card>
            <div className="grid gap-4 md:grid-cols-2">
              {view.holdings.map((h) => (
                <PortfolioHoldingCard key={h.id} holding={h} />
              ))}
            </div>
          </section>

          <section id="pf_allocations" className="scroll-mt-28 space-y-4">
            <h2 className="font-[family-name:var(--font-display)] text-2xl">Allocations</h2>
            <div className="grid gap-4 lg:grid-cols-2">
              <PortfolioAllocationChart view={view} />
              <PortfolioSectorChart view={view} />
              <SectorBarChart slices={view.allocations.industry} title="Industry allocation" />
              <SectorBarChart slices={view.allocations.marketCap} title="Market cap allocation" />
              <SectorBarChart slices={view.allocations.country} title="Country allocation" />
              <SectorBarChart slices={view.allocations.theme} title="Theme allocation" />
              <SectorBarChart slices={view.allocations.growthVsValue} title="Growth vs Value" />
              <SectorBarChart slices={view.allocations.dividendVsGrowth} title="Dividend vs Growth" />
              <SectorBarChart slices={view.allocations.cyclicalVsDefensive} title="Cyclical vs Defensive" />
              <WeightTreemap slices={view.allocations.sector} />
            </div>
          </section>

          <section id="pf_risk" className="scroll-mt-28 space-y-4">
            <h2 className="font-[family-name:var(--font-display)] text-2xl">Risk</h2>
            <PortfolioRiskMetrics view={view} />
            <PortfolioOpportunityCard view={view} />
          </section>

          <section id="pf_watchlist" className="scroll-mt-28 space-y-4">
            <h2 className="font-[family-name:var(--font-display)] text-2xl">Watchlist</h2>
            <div className="grid gap-4 md:grid-cols-2">
              {view.watchlist.map((w) => (
                <PortfolioWatchlistCard key={w.id} item={w} />
              ))}
            </div>
          </section>

          <section id="pf_rebalance" className="scroll-mt-28 space-y-4">
            <h2 className="font-[family-name:var(--font-display)] text-2xl">Rebalance</h2>
            <PortfolioRebalanceSuggestions items={view.rebalance} />
          </section>

          <section id="pf_scenarios" className="scroll-mt-28 space-y-4">
            <h2 className="font-[family-name:var(--font-display)] text-2xl">Scenarios</h2>
            <PortfolioScenarioAnalysis rows={view.scenarios} />
          </section>

          <section id="pf_expected" className="scroll-mt-28 space-y-4">
            <h2 className="font-[family-name:var(--font-display)] text-2xl">Expected return</h2>
            <PortfolioExpectedReturn view={view} />
            <PortfolioValuationSummary view={view} />
          </section>

          <section id="pf_quality" className="scroll-mt-28 space-y-4">
            <h2 className="font-[family-name:var(--font-display)] text-2xl">Quality &amp; moat</h2>
            <div className="grid gap-4 lg:grid-cols-2">
              <PortfolioQualityDistribution view={view} />
              <PortfolioMoatDistribution view={view} />
              <QualityHistogram slices={view.mosDistribution} title="MOS distribution" />
              <PortfolioDiversificationCard view={view} />
            </div>
          </section>

          <PortfolioExportPanel view={view} />

          <section id="pf_notes" className="scroll-mt-28">
            <PortfolioNotes notes={view.notes} disclosures={view.disclosures} />
          </section>
        </div>

        <aside className="hidden space-y-4 lg:block">
          <Card className="sticky top-28">
            <CardHeader title="On this page" />
            <CardBody>
              <ol className="space-y-1 text-sm">
                {PORTFOLIO_TOC.map((t, i) => (
                  <li key={t.id}>
                    <a href={`#${t.id}`} className="text-[var(--muted)] hover:text-[var(--fg)]">
                      {i + 1}. {t.title}
                    </a>
                  </li>
                ))}
              </ol>
            </CardBody>
          </Card>
        </aside>
      </div>

      <div className="fixed inset-x-0 bottom-0 z-30 flex gap-2 overflow-x-auto border-t border-[var(--border)] bg-[var(--surface)] p-2 md:hidden">
        <a href="#pf_overview" className="min-h-11 shrink-0 rounded-md border border-[var(--border)] px-3 py-2 text-xs">
          Overview
        </a>
        <a href="#pf_holdings" className="min-h-11 shrink-0 rounded-md border border-[var(--border)] px-3 py-2 text-xs">
          Holdings
        </a>
        <a href="#pf_risk" className="min-h-11 shrink-0 rounded-md border border-[var(--border)] px-3 py-2 text-xs">
          Risk
        </a>
        <a href="#pf_export" className="min-h-11 shrink-0 rounded-md border border-[var(--border)] px-3 py-2 text-xs">
          Export
        </a>
      </div>
    </div>
  );
});
