"use client";

/**
 * P2.3 — Institutional Valuation Transparency section.
 * Presentation of existing valuation outputs only.
 */

import { Badge } from "@/components/ds";
import type { ValuationTransparencyView } from "@/lib/valuation-transparency";
import { SectionCard } from "@/components/company-analysis/WorkspacePrimitives";

function MetricRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between gap-4 border-b border-[var(--border)] py-2 text-sm last:border-0 print:border-[var(--border)]">
      <dt className="text-[var(--muted)]">{label}</dt>
      <dd className="text-right font-medium text-[var(--fg)]">
        {value.trim() ? value : "Unavailable"}
      </dd>
    </div>
  );
}

export function ValuationTransparencySection({
  transparency,
}: {
  transparency: ValuationTransparencyView;
}) {
  const { executive, methods, consensus, marginOfSafety } = transparency;

  return (
    <div className="space-y-4 print:space-y-3">
      <p className="text-xs text-[var(--muted)]">{transparency.disclaimer}</p>

      <SectionCard
        title="Executive Valuation Card"
        description="Overall valuation remapped from existing institutional valuation rating and signals"
        action={<Badge variant="accent">{executive.grade}</Badge>}
      >
        <dl className="grid gap-0 sm:grid-cols-2">
          <MetricRow
            label="Overall Valuation Score"
            value={executive.overallScoreOutOf10}
          />
          <MetricRow label="Grade" value={executive.grade} />
          <MetricRow label="Confidence" value={executive.confidence} />
          <MetricRow
            label="Current Market Price"
            value={executive.currentMarketPrice}
          />
          <MetricRow label="Intrinsic Value" value={executive.intrinsicValue} />
          <MetricRow
            label="Margin of Safety"
            value={executive.marginOfSafety}
          />
          <MetricRow
            label="Valuation Verdict"
            value={executive.valuationVerdict}
          />
        </dl>
      </SectionCard>

      <SectionCard
        title="Valuation Method Cards"
        description="Existing engines only — weights and contributions stay Unavailable when not on the API"
      >
        <div className="grid gap-3 md:grid-cols-2 print:grid-cols-1">
          {methods.map((m) => (
            <article
              key={m.methodName}
              className="rounded-[var(--radius-md)] border border-[var(--border)] bg-[var(--surface)] p-3 print:break-inside-avoid"
              aria-label={`${m.methodName} valuation method`}
            >
              <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
                <h4 className="font-[family-name:var(--font-display)] text-sm tracking-tight text-[var(--fg)]">
                  {m.methodName}
                </h4>
                <Badge
                  variant={m.status === "Available" ? "accent" : "outline"}
                >
                  {m.status}
                </Badge>
              </div>
              <p className="mb-3 text-xs text-[var(--muted)]">{m.purpose}</p>
              <dl>
                <MetricRow label="Intrinsic Value" value={m.intrinsicValue} />
                <MetricRow label="Weight" value={m.weight} />
                <MetricRow
                  label="Contribution to Consensus"
                  value={m.contributionToConsensus}
                />
                <MetricRow label="Confidence" value={m.confidence} />
                <MetricRow
                  label="Data Completeness"
                  value={m.dataCompleteness}
                />
                <MetricRow label="Missing Inputs" value={m.missingInputs} />
                <MetricRow
                  label="Assumptions Used"
                  value={m.assumptionsUsed}
                />
              </dl>
              <p className="mt-2 text-xs leading-relaxed text-[var(--fg)]">
                {m.explanation}
              </p>
              <p className="mt-1 text-[10px] text-[var(--muted)]">
                Source: {m.sourceField}
              </p>
            </article>
          ))}
        </div>
      </SectionCard>

      <div className="grid gap-4 lg:grid-cols-2">
        <SectionCard title="Consensus Panel">
          <dl>
            <MetricRow
              label="Highest Valuation"
              value={consensus.highestValuation}
            />
            <MetricRow
              label="Lowest Valuation"
              value={consensus.lowestValuation}
            />
            <MetricRow
              label="Consensus Value"
              value={consensus.consensusValue}
            />
            <MetricRow
              label="Dispersion Indicator"
              value={consensus.dispersionIndicator}
            />
            <MetricRow
              label="Number of Methods Used"
              value={consensus.numberOfMethodsUsed}
            />
          </dl>
        </SectionCard>

        <SectionCard title="Margin of Safety Panel">
          <dl>
            <MetricRow
              label="Current Price"
              value={marginOfSafety.currentPrice}
            />
            <MetricRow
              label="Consensus Intrinsic Value"
              value={marginOfSafety.consensusIntrinsicValue}
            />
            <MetricRow
              label="Margin of Safety"
              value={marginOfSafety.marginOfSafety}
            />
            <MetricRow
              label="Valuation Category"
              value={marginOfSafety.valuationCategory}
            />
          </dl>
        </SectionCard>
      </div>

      <SectionCard
        title="Method Confidence"
        description="Per-method confidence and completeness from existing stage outputs only"
      >
        <div className="overflow-x-auto">
          <table className="w-full min-w-[32rem] border-collapse text-sm">
            <thead>
              <tr className="border-b border-[var(--border)] text-left text-[var(--muted)]">
                <th className="py-2 pr-3 font-medium">Method</th>
                <th className="py-2 pr-3 font-medium">Confidence</th>
                <th className="py-2 pr-3 font-medium">Data Completeness</th>
                <th className="py-2 pr-3 font-medium">Missing Inputs</th>
                <th className="py-2 font-medium">Assumptions Used</th>
              </tr>
            </thead>
            <tbody>
              {methods.map((m) => (
                <tr
                  key={`conf-${m.methodName}`}
                  className="border-b border-[var(--border)] last:border-0"
                >
                  <td className="py-2 pr-3">{m.methodName}</td>
                  <td className="py-2 pr-3">{m.confidence}</td>
                  <td className="py-2 pr-3">{m.dataCompleteness}</td>
                  <td className="py-2 pr-3">{m.missingInputs}</td>
                  <td className="py-2">{m.assumptionsUsed}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </SectionCard>
    </div>
  );
}
