"use client";

/**
 * Portfolio Intelligence Engine (RC1 Milestone 4) — presentation only.
 * Health Score, AI Summary, Recommendation Cards, Risk Summary, Valuation
 * Heatmap, Opportunity Ranking, Diversification Analysis (incl.
 * Concentration + Sector/Style Drift), Scenario Analysis. All values come
 * from POST /api/v1/portfolio/insights — never recomputed in the browser.
 * Honest "Data unavailable." when the server could not compute a value.
 */

import { Badge } from "@/components/ds";
import type {
  ConcentrationView,
  DiversificationView,
  DriftView,
  HealthScoreView,
  OpportunitiesView,
  PortfolioInsightsView,
  RecommendationView,
  RiskSummaryView,
  ScenarioView,
  ValuationHeatmapView,
} from "@/lib/portfolio-intelligence/mapPortfolioInsights";
import { FieldRow, SectionCard, WorkspaceEmpty, WorkspaceSkeleton } from "./Primitives";

function LoadingOr({ isLoading, children }: { isLoading: boolean; children: React.ReactNode }) {
  if (isLoading) return <WorkspaceSkeleton />;
  return <>{children}</>;
}

function Limitations({ items }: { items: string[] }) {
  if (!items.length) return null;
  return (
    <ul className="mt-3 list-disc space-y-1 pl-4 text-xs text-[var(--muted)]">
      {items.map((l) => (
        <li key={l}>{l}</li>
      ))}
    </ul>
  );
}

const ACTION_VARIANT: Record<string, "accent" | "outline" | "danger"> = {
  increase: "accent",
  reduce: "danger",
  hold: "outline",
  review: "outline",
  watch: "outline",
};

export function HealthScoreSection({
  health,
  isLoading,
}: {
  health: HealthScoreView;
  isLoading: boolean;
}) {
  return (
    <SectionCard
      title="Portfolio Health Score"
      description="Weighted combination of Diversification, Risk, Valuation, Financial Quality, Concentration, and Cash Allocation — every sub-score explained, unavailable inputs excluded (never fabricated)"
    >
      <LoadingOr isLoading={isLoading}>
        {!health.available ? (
          <WorkspaceEmpty description="Data unavailable. Add holdings to compute a Portfolio Health Score." />
        ) : (
          <div className="space-y-4">
            <div className="flex items-baseline gap-3">
              <span className="text-3xl font-semibold text-[var(--fg)]">{health.scoreLabel}</span>
              <Badge variant="outline">{health.status}</Badge>
            </div>
            <dl>
              {health.components.map((c) => (
                <FieldRow
                  key={c.name}
                  label={`${c.name.replace(/_/g, " ")} (weight ${c.weightPct})`}
                  value={c.available ? `${c.score} · ${c.explanation}` : c.explanation}
                />
              ))}
            </dl>
          </div>
        )}
      </LoadingOr>
      <Limitations items={health.limitations} />
    </SectionCard>
  );
}

export function AiSummarySection({
  insights,
  isLoading,
}: {
  insights: PortfolioInsightsView;
  isLoading: boolean;
}) {
  const topRecommendations = insights.recommendations.slice(0, 3);
  return (
    <SectionCard
      title="AI Summary"
      description="Condensed overview of the Portfolio Intelligence Engine result — every figure is surfaced from the sections below, never separately computed"
    >
      <LoadingOr isLoading={isLoading}>
        {!insights.available ? (
          <WorkspaceEmpty description="Data unavailable." />
        ) : (
          <div className="space-y-4">
            <FieldRow label="Holdings analysed" value={insights.holdingCount} />
            <FieldRow label="Health Score" value={insights.health.scoreLabel} />
            <FieldRow
              label="Base Case implied return"
              value={
                insights.scenario.cases.find((c) => c.case === "Base")?.impliedReturnPct ??
                "Data unavailable."
              }
            />
            <FieldRow label="Expected CAGR (trailing, historical)" value={insights.scenario.expectedCagr} />
            <FieldRow label="Worst-case drawdown (trailing, historical)" value={insights.scenario.worstCaseDrawdown} />
            <div>
              <p className="mb-2 text-sm text-[var(--muted)]">Top recommendations</p>
              {topRecommendations.length === 0 ? (
                <WorkspaceEmpty description="Data unavailable." />
              ) : (
                <ul className="space-y-2">
                  {topRecommendations.map((r) => (
                    <li key={r.symbol} className="flex items-center gap-2 text-sm">
                      <Badge variant={ACTION_VARIANT[r.action] ?? "outline"}>{r.actionLabel}</Badge>
                      <span className="font-mono">{r.symbol}</span>
                      <span className="text-[var(--muted)]">{r.reason}</span>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </div>
        )}
      </LoadingOr>
      <Limitations items={insights.limitations} />
    </SectionCard>
  );
}

export function RecommendationCardsSection({
  recommendations,
  isLoading,
}: {
  recommendations: RecommendationView[];
  isLoading: boolean;
}) {
  return (
    <SectionCard
      title="AI Recommendations"
      description="Rule-based combination of existing valuation/quality/risk signals — Increase/Reduce/Hold/Review/Watch. Every recommendation cites its reason and confidence; never a new AI model"
    >
      <LoadingOr isLoading={isLoading}>
        {recommendations.length === 0 ? (
          <WorkspaceEmpty description="Data unavailable." />
        ) : (
          <ul className="grid gap-3 sm:grid-cols-2" aria-label="Portfolio recommendations">
            {recommendations.map((r) => (
              <li
                key={r.symbol}
                className="rounded-[var(--radius-md)] border border-[var(--border)] p-3"
              >
                <div className="mb-1 flex items-center justify-between gap-2">
                  <span className="font-mono font-medium">{r.symbol}</span>
                  <Badge variant={ACTION_VARIANT[r.action] ?? "outline"}>{r.actionLabel}</Badge>
                </div>
                <p className="text-sm text-[var(--muted)]">{r.reason}</p>
                <p className="mt-1 text-xs text-[var(--muted)]">Confidence: {r.confidence}</p>
              </li>
            ))}
          </ul>
        )}
      </LoadingOr>
    </SectionCard>
  );
}

export function RiskSummarySection({
  risk,
  isLoading,
}: {
  risk: RiskSummaryView;
  isLoading: boolean;
}) {
  return (
    <SectionCard
      title="Portfolio Risk Summary"
      description="Beta, Volatility, Max Drawdown, Value at Risk, Stress Results, Monte Carlo, Tracking Error — aggregation and highlighting of Portfolio Analytics output only"
    >
      <LoadingOr isLoading={isLoading}>
        {!risk.available ? (
          <WorkspaceEmpty description="Data unavailable." />
        ) : (
          <div className="space-y-4">
            <dl>
              <FieldRow label="Beta" value={risk.beta} />
              <FieldRow label="Annualized volatility" value={risk.annualizedVolatility} />
              <FieldRow label="Max drawdown" value={risk.maxDrawdown} />
              <FieldRow label="Tracking error" value={risk.trackingError} />
              <FieldRow
                label="Value at Risk (95%)"
                value={
                  risk.valueAtRisk95 === "Data unavailable."
                    ? risk.valueAtRisk95
                    : `${risk.valueAtRisk95} (${risk.valueAtRiskMethod})`
                }
              />
              <FieldRow label="Conditional VaR (95%)" value={risk.conditionalValueAtRisk95} />
              <FieldRow label="Stress scenarios run" value={risk.stressTestCount} />
              <FieldRow label="Monte Carlo available" value={risk.monteCarloAvailable ? "Yes" : "Data unavailable."} />
            </dl>
            <div>
              <p className="mb-2 text-sm text-[var(--muted)]">Highest-risk holdings</p>
              {risk.highestRiskHoldings.length === 0 ? (
                <WorkspaceEmpty description="Data unavailable." />
              ) : (
                <table className="min-w-full text-xs">
                  <thead>
                    <tr>
                      <th className="p-1 text-left">Symbol</th>
                      <th className="p-1 text-left">Weight</th>
                      <th className="p-1 text-left">Volatility</th>
                      <th className="p-1 text-left">Risk contribution</th>
                    </tr>
                  </thead>
                  <tbody>
                    {risk.highestRiskHoldings.map((h) => (
                      <tr key={h.symbol}>
                        <td className="p-1 font-mono">{h.symbol}</td>
                        <td className="p-1">{h.weight}</td>
                        <td className="p-1">{h.volatility}</td>
                        <td className="p-1">{h.riskContributionPct}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          </div>
        )}
      </LoadingOr>
      <Limitations items={risk.limitations} />
    </SectionCard>
  );
}

const VALUATION_BADGE: Record<string, "accent" | "outline" | "danger"> = {
  Undervalued: "accent",
  "Fairly Valued": "outline",
  Overvalued: "danger",
};

export function ValuationHeatmapSection({
  heatmap,
  isLoading,
}: {
  heatmap: ValuationHeatmapView;
  isLoading: boolean;
}) {
  return (
    <SectionCard
      title="Valuation Heatmap"
      description="Classifies each holding Undervalued / Fairly Valued / Overvalued from its linked margin of safety — reuses the Valuation Engine only, no new valuation math"
    >
      <LoadingOr isLoading={isLoading}>
        {heatmap.rows.length === 0 ? (
          <WorkspaceEmpty description="Data unavailable." />
        ) : (
          <>
            <div className="mb-3 flex flex-wrap gap-4 text-xs text-[var(--muted)]">
              <span>Undervalued: {heatmap.undervaluedWeight}</span>
              <span>Fairly Valued: {heatmap.fairlyValuedWeight}</span>
              <span>Overvalued: {heatmap.overvaluedWeight}</span>
              <span>Data unavailable: {heatmap.unavailableWeight}</span>
            </div>
            <ul className="grid gap-2 sm:grid-cols-2" aria-label="Valuation heatmap">
              {heatmap.rows.map((r) => (
                <li
                  key={r.symbol}
                  className="flex items-center justify-between gap-2 rounded-[var(--radius-md)] border border-[var(--border)] p-2 text-sm"
                >
                  <span className="font-mono">{r.symbol}</span>
                  <Badge variant={VALUATION_BADGE[r.valuationClass] ?? "outline"}>
                    {r.valuationClass}
                  </Badge>
                  <span className="text-xs text-[var(--muted)]">MoS: {r.marginOfSafety}</span>
                </li>
              ))}
            </ul>
          </>
        )}
      </LoadingOr>
      <Limitations items={heatmap.limitations} />
    </SectionCard>
  );
}

function OpportunityList({
  title,
  entries,
}: {
  title: string;
  entries: Array<{ symbol: string; value: string }>;
}) {
  return (
    <div>
      <p className="mb-1 text-sm font-medium">{title}</p>
      {entries.length === 0 ? (
        <p className="text-xs text-[var(--muted)]">Data unavailable.</p>
      ) : (
        <ol className="space-y-1 text-sm">
          {entries.map((e) => (
            <li key={e.symbol} className="flex justify-between gap-2">
              <span className="font-mono">{e.symbol}</span>
              <span className="text-[var(--muted)]">{e.value}</span>
            </li>
          ))}
        </ol>
      )}
    </div>
  );
}

export function OpportunityRankingSection({
  opportunities,
  isLoading,
}: {
  opportunities: OpportunitiesView;
  isLoading: boolean;
}) {
  return (
    <SectionCard
      title="Portfolio Opportunity Finder"
      description="Ranks existing holdings by already-computed signals — Margin of Safety, Business Quality, Risk Attribution, Committee Confidence. 'Highest Expected CAGR' is honestly unavailable: no engine produces a forward-looking per-company CAGR"
    >
      <LoadingOr isLoading={isLoading}>
        {!opportunities.available ? (
          <WorkspaceEmpty description="Data unavailable." />
        ) : (
          <div className="grid gap-4 sm:grid-cols-2">
            <OpportunityList title="Highest Margin of Safety" entries={opportunities.highestMarginOfSafety} />
            <OpportunityList title="Highest Expected CAGR" entries={opportunities.highestExpectedCagr} />
            <OpportunityList title="Best Quality" entries={opportunities.bestQuality} />
            <OpportunityList title="Lowest Risk" entries={opportunities.lowestRisk} />
            <OpportunityList title="Highest Conviction" entries={opportunities.highestConviction} />
          </div>
        )}
      </LoadingOr>
      <Limitations items={opportunities.limitations} />
    </SectionCard>
  );
}

export function DiversificationAnalysisSection({
  diversification,
  concentration,
  drift,
  isLoading,
}: {
  diversification: DiversificationView;
  concentration: ConcentrationView;
  drift: DriftView;
  isLoading: boolean;
}) {
  return (
    <div className="space-y-4">
      <SectionCard
        title="Diversification Score"
        description="Combines holding count, sector spread, position sizing, and return correlation — every input already computed by Portfolio Analytics or this orchestration layer"
      >
        <LoadingOr isLoading={isLoading}>
          {!diversification.available ? (
            <WorkspaceEmpty description="Data unavailable." />
          ) : (
            <div className="space-y-2">
              <div className="flex items-baseline gap-3">
                <span className="text-2xl font-semibold">{diversification.score}</span>
                <Badge variant="outline">{diversification.status}</Badge>
              </div>
              <ul className="list-disc space-y-1 pl-4 text-sm text-[var(--muted)]">
                {diversification.explanation.map((e) => (
                  <li key={e}>{e}</li>
                ))}
              </ul>
            </div>
          )}
        </LoadingOr>
        <Limitations items={diversification.limitations} />
      </SectionCard>

      <SectionCard
        title="Concentration Analysis"
        description="Largest holdings and sector/industry/style/country concentration — flags excessive exposure against disclosed thresholds"
      >
        <LoadingOr isLoading={isLoading}>
          {!concentration.available ? (
            <WorkspaceEmpty description="Data unavailable." />
          ) : (
            <div className="space-y-3">
              {concentration.flags.length > 0 ? (
                <ul className="flex flex-wrap gap-2">
                  {concentration.flags.map((f, i) => (
                    <li key={`${f.kind}-${f.label}-${i}`}>
                      <Badge variant="danger">
                        {f.label} · {f.weight} ({f.kind})
                      </Badge>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="text-sm text-[var(--muted)]">No excessive concentration flagged.</p>
              )}
              <div>
                <p className="mb-1 text-sm font-medium">Largest holdings</p>
                <ol className="space-y-1 text-sm">
                  {concentration.largestHoldings.map((h) => (
                    <li key={h.symbol} className="flex justify-between gap-2">
                      <span className="font-mono">{h.symbol}</span>
                      <span className="text-[var(--muted)]">{h.weight}</span>
                    </li>
                  ))}
                </ol>
              </div>
            </div>
          )}
        </LoadingOr>
        <Limitations items={concentration.limitations} />
      </SectionCard>

      <SectionCard
        title="Sector & Style Drift"
        description="Deviation from an even-split reference baseline (11 GICS sectors) — overweight/underweight/missing sectors; style and cap-size drift require caller-declared labels"
      >
        <LoadingOr isLoading={isLoading}>
          {!drift.available && drift.sectorDrift.length === 0 ? (
            <WorkspaceEmpty description="Data unavailable." />
          ) : (
            <div className="space-y-3">
              <div>
                <p className="mb-1 text-sm font-medium">Sector drift</p>
                <ul className="space-y-1 text-sm">
                  {drift.sectorDrift.map((d) => (
                    <li key={d.label} className="flex justify-between gap-2">
                      <span>{d.label}</span>
                      <span className="text-[var(--muted)]">
                        {d.weight} vs {d.baseline} baseline — {d.direction}
                      </span>
                    </li>
                  ))}
                </ul>
              </div>
              {drift.missingSectors.length > 0 ? (
                <p className="text-xs text-[var(--muted)]">
                  Missing sectors: {drift.missingSectors.join(", ")}
                </p>
              ) : null}
            </div>
          )}
        </LoadingOr>
        <Limitations items={drift.limitations} />
      </SectionCard>
    </div>
  );
}

export function ScenarioAnalysisSection({
  scenario,
  isLoading,
}: {
  scenario: ScenarioView;
  isLoading: boolean;
}) {
  return (
    <SectionCard
      title="Portfolio AI Committee — Scenario Summary"
      description="Bull/Base/Bear synthesis from already-linked valuation signals and the portfolio's own trailing volatility/return — a disclosed aggregation, never a new AI Committee vote or valuation re-run"
    >
      <LoadingOr isLoading={isLoading}>
        {!scenario.available ? (
          <WorkspaceEmpty description="Data unavailable." />
        ) : (
          <div className="space-y-4">
            <ul className="grid gap-3 sm:grid-cols-3" aria-label="Bull/Base/Bear cases">
              {scenario.cases.map((c) => (
                <li
                  key={c.case}
                  className="rounded-[var(--radius-md)] border border-[var(--border)] p-3 text-center"
                >
                  <p className="text-xs uppercase tracking-wide text-[var(--muted)]">{c.case}</p>
                  <p className="text-lg font-semibold">{c.impliedReturnPct}</p>
                </li>
              ))}
            </ul>
            <dl>
              <FieldRow label="Expected CAGR" value={scenario.expectedCagr} />
              <FieldRow label="Basis" value={scenario.expectedCagrBasis} />
              <FieldRow label="Worst-case drawdown" value={scenario.worstCaseDrawdown} />
              <FieldRow label="Basis" value={scenario.worstCaseDrawdownBasis} />
              <FieldRow label="Confidence" value={scenario.confidence} />
              <FieldRow label="Basis" value={scenario.confidenceBasis} />
            </dl>
          </div>
        )}
      </LoadingOr>
      <Limitations items={scenario.limitations} />
    </SectionCard>
  );
}
