"use client";

/**
 * Portfolio Intelligence Analytics module (additive) — presentation only.
 * Correlation Matrix, Efficient Frontier, Monte Carlo, Stress Testing,
 * Scenario Analysis, Tax Optimization, Position Limits, Factor Exposure.
 * All values come from POST /api/v1/portfolio/analytics/* — never
 * recomputed in the browser. Honest "Data unavailable." when the server
 * could not compute a value from the supplied session holdings.
 */

import type {
  ConstraintsView,
  RiskView,
  SimulationView,
  StressView,
  TaxView,
} from "@/lib/portfolio-intelligence/mapPortfolioAnalytics";
import { FieldRow, SectionCard, WorkspaceEmpty, WorkspaceSkeleton } from "./Primitives";

function LoadingOr({
  isLoading,
  children,
}: {
  isLoading: boolean;
  children: React.ReactNode;
}) {
  if (isLoading) return <WorkspaceSkeleton />;
  return <>{children}</>;
}

/** Simple color-scaled correlation table — no chart dependency. */
function correlationCellClass(value: number | null): string {
  if (value === null || !Number.isFinite(value)) return "bg-[var(--surface-2)]";
  if (value >= 0.7) return "bg-[var(--danger-soft,#fee2e2)]";
  if (value >= 0.3) return "bg-[var(--warning-soft,#fef3c7)]";
  if (value <= -0.3) return "bg-[var(--accent-soft)]";
  return "bg-[var(--surface-2)]";
}

export function CorrelationMatrixSection({
  risk,
  isLoading,
}: {
  risk: RiskView;
  isLoading: boolean;
}) {
  const symbols = risk.correlationSymbols;
  const matrix = risk.correlationMatrix;
  return (
    <div className="space-y-4">
      <SectionCard
        title="Correlation Matrix"
        description="Pairwise return correlation across session holdings — server-computed from authenticated price history"
      >
        <LoadingOr isLoading={isLoading}>
          {symbols.length === 0 ? (
            <WorkspaceEmpty description="Data unavailable. Requires overlapping authenticated price history across at least 2 holdings." />
          ) : (
            <div className="overflow-x-auto">
              <table className="min-w-full border-collapse text-xs" aria-label="Correlation matrix">
                <thead>
                  <tr>
                    <th className="p-1 text-left" />
                    {symbols.map((s) => (
                      <th key={s} scope="col" className="p-1 font-mono">
                        {s}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {symbols.map((rowSymbol, i) => (
                    <tr key={rowSymbol}>
                      <th scope="row" className="p-1 text-left font-mono">
                        {rowSymbol}
                      </th>
                      {symbols.map((colSymbol, j) => {
                        const value = matrix[i]?.[j] ?? null;
                        return (
                          <td
                            key={colSymbol}
                            className={`p-1 text-center ${correlationCellClass(value)}`}
                          >
                            {value === null ? "—" : value.toFixed(2)}
                          </td>
                        );
                      })}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </LoadingOr>
      </SectionCard>
    </div>
  );
}

export function FactorExposureSection({
  risk,
  isLoading,
}: {
  risk: RiskView;
  isLoading: boolean;
}) {
  return (
    <div className="space-y-4">
      <SectionCard
        title="Factor Exposure"
        description="Portfolio-weighted rollup of Value/Quality/Momentum/Size/Low-volatility — aggregation only, no new fundamental scoring"
      >
        <LoadingOr isLoading={isLoading}>
          {risk.factors.length === 0 ? (
            <WorkspaceEmpty description="Data unavailable." />
          ) : (
            <ul className="space-y-2" aria-label="Factor exposure">
              {risk.factors.map((f) => (
                <li key={f.factorName}>
                  <div className="mb-1 flex justify-between gap-2 text-sm">
                    <span className="capitalize">{f.factorName.replace("_", " ")}</span>
                    <span className="text-[var(--muted)]">
                      {f.exposureValue} · {f.coverage}
                    </span>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </LoadingOr>
        {risk.limitations.length ? (
          <ul className="mt-3 list-disc space-y-1 pl-4 text-xs text-[var(--muted)]">
            {risk.limitations.map((l) => (
              <li key={l}>{l}</li>
            ))}
          </ul>
        ) : null}
      </SectionCard>
    </div>
  );
}

export function EfficientFrontierSection({
  simulation,
  isLoading,
}: {
  simulation: SimulationView;
  isLoading: boolean;
}) {
  const maxReturn = Math.max(
    ...simulation.frontierPoints.map((p) => parseFloat(p.expectedReturn) || 0),
    1,
  );
  const maxVol = Math.max(
    ...simulation.frontierPoints.map((p) => parseFloat(p.volatility) || 0),
    1,
  );
  return (
    <div className="space-y-4">
      <SectionCard
        title="Efficient Frontier"
        description="Mean-variance random-weight sampling over historical returns — an approximation, never a closed-form optimization"
      >
        <LoadingOr isLoading={isLoading}>
          {simulation.frontierPoints.length === 0 ? (
            <WorkspaceEmpty description="Data unavailable. Requires at least 2 holdings with overlapping price history." />
          ) : (
            <>
              <svg
                viewBox="0 0 220 140"
                className="mb-3 h-40 w-full"
                role="img"
                aria-label="Efficient frontier scatter plot: expected return vs. volatility"
              >
                <line x1="20" y1="120" x2="210" y2="120" stroke="var(--border)" />
                <line x1="20" y1="10" x2="20" y2="120" stroke="var(--border)" />
                {simulation.frontierPoints.map((p, i) => {
                  const ret = parseFloat(p.expectedReturn) || 0;
                  const vol = parseFloat(p.volatility) || 0;
                  const x = 20 + (vol / maxVol) * 180;
                  const y = 120 - (ret / maxReturn) * 100;
                  return (
                    <circle
                      key={i}
                      cx={x}
                      cy={Math.max(10, Math.min(120, y))}
                      r={2.5}
                      fill="var(--accent)"
                    />
                  );
                })}
                {simulation.currentPortfolioPoint ? (
                  <circle
                    cx={
                      20 +
                      ((parseFloat(simulation.currentPortfolioPoint.volatility) || 0) /
                        maxVol) *
                        180
                    }
                    cy={Math.max(
                      10,
                      Math.min(
                        120,
                        120 -
                          ((parseFloat(simulation.currentPortfolioPoint.expectedReturn) || 0) /
                            maxReturn) *
                            100,
                      ),
                    )}
                    r={4}
                    fill="var(--danger,#ef4444)"
                  />
                ) : null}
              </svg>
              <div className="overflow-x-auto">
                <table className="min-w-full text-xs">
                  <thead>
                    <tr>
                      <th className="p-1 text-left">Expected return</th>
                      <th className="p-1 text-left">Volatility</th>
                    </tr>
                  </thead>
                  <tbody>
                    {simulation.frontierPoints.slice(0, 15).map((p, i) => (
                      <tr key={i}>
                        <td className="p-1">{p.expectedReturn}</td>
                        <td className="p-1">{p.volatility}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          )}
        </LoadingOr>
        {simulation.frontierLimitations.length ? (
          <ul className="mt-3 list-disc space-y-1 pl-4 text-xs text-[var(--muted)]">
            {simulation.frontierLimitations.map((l) => (
              <li key={l}>{l}</li>
            ))}
          </ul>
        ) : null}
      </SectionCard>
    </div>
  );
}

export function MonteCarloSection({
  simulation,
  isLoading,
}: {
  simulation: SimulationView;
  isLoading: boolean;
}) {
  return (
    <div className="space-y-4">
      <SectionCard
        title="Monte Carlo Simulation"
        description="Bootstrap resampling of historical daily returns — never a probabilistic guarantee"
      >
        <LoadingOr isLoading={isLoading}>
          <dl>
            <FieldRow label="Status" value={simulation.monteCarloStatus} />
            <FieldRow label="Paths" value={simulation.monteCarloPaths} />
            <FieldRow label="Horizon (days)" value={simulation.monteCarloHorizonDays} />
            <FieldRow label="Mean terminal return" value={simulation.meanTerminalReturn} />
          </dl>
          {simulation.percentiles.length === 0 ? (
            <WorkspaceEmpty description="Data unavailable." />
          ) : (
            <ul className="mt-3 space-y-1 text-sm" aria-label="Terminal return percentiles">
              {simulation.percentiles.map((p) => (
                <li key={p.label} className="flex justify-between gap-2">
                  <span className="font-mono uppercase">{p.label}</span>
                  <span>{p.value}</span>
                </li>
              ))}
            </ul>
          )}
        </LoadingOr>
        {simulation.monteCarloLimitations.length ? (
          <ul className="mt-3 list-disc space-y-1 pl-4 text-xs text-[var(--muted)]">
            {simulation.monteCarloLimitations.map((l) => (
              <li key={l}>{l}</li>
            ))}
          </ul>
        ) : null}
      </SectionCard>
    </div>
  );
}

export function StressTestingSection({
  stress,
  isLoading,
}: {
  stress: StressView;
  isLoading: boolean;
}) {
  return (
    <div className="space-y-4">
      <SectionCard
        title="Stress Testing"
        description="Historical crash-window replay using each holding's actual returns when available, else beta-scaled shock"
      >
        <LoadingOr isLoading={isLoading}>
          {stress.stressTests.length === 0 ? (
            <WorkspaceEmpty description="Data unavailable." />
          ) : (
            <ul className="space-y-3" aria-label="Stress test results">
              {stress.stressTests.map((t) => (
                <li
                  key={t.scenarioId}
                  className="rounded-[var(--radius-md)] border border-[var(--border)] p-3"
                >
                  <div className="mb-1 flex justify-between gap-2 text-sm font-medium">
                    <span>{t.description}</span>
                    <span>{t.available ? t.portfolioReturnPct : "Data unavailable."}</span>
                  </div>
                  {t.available ? (
                    <p className="text-xs text-[var(--muted)]">
                      {t.positionsWithHistory} position(s) used actual history ·{" "}
                      {t.positionsBetaScaled} beta-scaled
                    </p>
                  ) : (
                    <p className="text-xs text-[var(--muted)]">{t.message}</p>
                  )}
                </li>
              ))}
            </ul>
          )}
        </LoadingOr>
      </SectionCard>
      <SectionCard title="Available crash windows">
        {stress.catalog.length === 0 ? (
          <WorkspaceEmpty description="Data unavailable." />
        ) : (
          <ul className="space-y-1 text-sm">
            {stress.catalog.map((c) => (
              <li key={c.id} className="flex justify-between gap-2">
                <span>{c.description}</span>
                <span className="text-xs text-[var(--muted)]">
                  {c.start} → {c.end}
                </span>
              </li>
            ))}
          </ul>
        )}
      </SectionCard>
    </div>
  );
}

export function ScenarioImpactSection({
  stress,
  isLoading,
}: {
  stress: StressView;
  isLoading: boolean;
}) {
  return (
    <div className="space-y-4">
      <SectionCard
        title="Scenario Analysis"
        description="Caller-defined shocks applied via beta-implied sensitivity per holding"
      >
        <LoadingOr isLoading={isLoading}>
          {stress.scenarios.length === 0 ? (
            <WorkspaceEmpty description="Data unavailable." />
          ) : (
            <ul className="space-y-2" aria-label="Scenario impacts">
              {stress.scenarios.map((s) => (
                <li key={s.name} className="flex justify-between gap-2 text-sm">
                  <span>
                    {s.name} ({s.shockPct})
                  </span>
                  <span className="font-medium">{s.portfolioImpactPct}</span>
                </li>
              ))}
            </ul>
          )}
        </LoadingOr>
        <p className="mt-3 text-xs text-[var(--muted)]">
          Default scenarios shown; a custom shock input is not yet wired in this
          workspace revision.
        </p>
      </SectionCard>
    </div>
  );
}

export function TaxOptimizationSection({
  tax,
  isLoading,
}: {
  tax: TaxView;
  isLoading: boolean;
}) {
  return (
    <div className="space-y-4">
      <SectionCard
        title="Tax Optimization"
        description="Unrealized gain/loss and holding-period classification — requires caller-supplied cost basis and purchase date per position"
      >
        <LoadingOr isLoading={isLoading}>
          <dl>
            <FieldRow label="Status" value={tax.status} />
            <FieldRow
              label="Loss-harvesting candidates"
              value={tax.harvestingCandidates.length ? tax.harvestingCandidates.join(", ") : "None"}
            />
          </dl>
          {tax.lots.length === 0 ? (
            <WorkspaceEmpty description="Data unavailable. Session holdings do not carry cost_basis_per_unit or purchase_date." />
          ) : (
            <ul className="mt-3 space-y-1 text-sm" aria-label="Tax lots">
              {tax.lots.map((l) => (
                <li key={l.symbol} className="flex justify-between gap-2">
                  <span className="font-mono text-xs">{l.symbol}</span>
                  <span>
                    {l.available ? `${l.gainLossPct} · ${l.term}` : l.reasonUnavailable}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </LoadingOr>
        {tax.limitations.length ? (
          <ul className="mt-3 list-disc space-y-1 pl-4 text-xs text-[var(--muted)]">
            {tax.limitations.map((l) => (
              <li key={l}>{l}</li>
            ))}
          </ul>
        ) : null}
      </SectionCard>
    </div>
  );
}

export function PositionLimitsSection({
  constraints,
  isLoading,
}: {
  constraints: ConstraintsView;
  isLoading: boolean;
}) {
  return (
    <div className="space-y-4">
      <SectionCard
        title="Position Limits"
        description="Breach checks against caller-supplied max-position/max-sector/min-cash limits"
      >
        <LoadingOr isLoading={isLoading}>
          <dl>
            <FieldRow label="Status" value={constraints.limitsStatus} />
          </dl>
          {constraints.checks.length === 0 ? (
            <WorkspaceEmpty description="Data unavailable. No limits configured for this session — position-limit checks require a max_position_weight, max_sector_weight, or min_cash_weight input." />
          ) : (
            <ul className="mt-3 space-y-1 text-sm" aria-label="Position limit checks">
              {constraints.checks.map((c) => (
                <li key={`${c.limitType}-${c.label}`} className="flex justify-between gap-2">
                  <span>
                    {c.label} ({c.limitType})
                  </span>
                  <span className={c.breached ? "font-medium text-[var(--danger,#ef4444)]" : ""}>
                    {c.actual} / {c.limit}
                    {c.breached ? " — breached" : ""}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </LoadingOr>
      </SectionCard>
    </div>
  );
}
