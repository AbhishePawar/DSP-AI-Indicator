"use client";

import Link from "next/link";

import { MarketDataCard } from "@/components/market/MarketDataCard";
import { DeterministicAnalysisLabel } from "@/components/market/MarketStatusIndicator";
import { Button } from "@/components/ui/Button";
import { Card, CardBody, CardHeader } from "@/components/ui/Card";
import { formatPct, formatScore } from "@/lib/intelligence/mapResponse";
import type { IntelligenceView } from "@/lib/intelligence/mapResponse";

export function AnalysisSummary({
  view,
  intrinsicValue,
  ticker,
}: {
  view: IntelligenceView;
  intrinsicValue?: string | null;
  ticker?: string | null;
}) {
  return (
    <div className="space-y-4">
      <Card>
        <CardHeader
          title="Analysis Summary"
          description="Key composition outputs from /api/v1/analyse"
          action={<DeterministicAnalysisLabel />}
        />
        <CardBody>
          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
            <Metric label="Recommendation" value={view.recommendation} emphasize />
            <Metric
              label="Intrinsic Value"
              value={intrinsicValue || "Unavailable"}
            />
            <Metric
              label="Margin of Safety"
              value={formatPct(view.marginOfSafety)}
            />
            <Metric
              label="Overall Quality"
              value={`${view.businessQualityLabel} · ${formatScore(view.businessQualityScore)}`}
            />
            <Metric
              label="Committee Decision"
              value={view.committeeDecision}
              emphasize
            />
            <Metric
              label="Committee Confidence"
              value={formatPct(view.committeeConfidence)}
            />
          </div>
        </CardBody>
      </Card>

      {ticker ? <MarketDataCard ticker={ticker} /> : null}
    </div>
  );
}

function Metric({
  label,
  value,
  emphasize,
}: {
  label: string;
  value: string;
  emphasize?: boolean;
}) {
  return (
    <div>
      <p className="text-xs text-[var(--muted)]">{label}</p>
      <p
        className={
          emphasize
            ? "mt-1 font-[family-name:var(--font-display)] text-xl tracking-tight"
            : "mt-1 text-sm font-medium"
        }
      >
        {value}
      </p>
    </div>
  );
}

export function AnalysisSummaryEmpty() {
  return (
    <Card>
      <CardHeader title="Analysis Summary" />
      <CardBody>
        <p className="text-sm text-[var(--muted)]">
          Run analysis to populate recommendation, valuation, quality, and
          committee outputs.
        </p>
        <Link href="/companies" className="mt-3 inline-block text-sm underline">
          Browse companies
        </Link>
      </CardBody>
    </Card>
  );
}
