"use client";

import { Card, CardBody, CardHeader } from "@/components/ui/Card";
import {
  formatPct,
  formatScore,
} from "@/lib/intelligence/mapResponse";

export function BusinessQualityCard({
  label,
  score,
  confidence,
}: {
  label: string;
  score: number | null;
  confidence: number | null;
}) {
  return (
    <Card>
      <CardHeader
        title="Business Quality Summary"
        description="Aggregator stage summary from the API"
      />
      <CardBody className="grid gap-3 sm:grid-cols-3">
        <Metric label="Overall quality" value={label} />
        <Metric label="Score" value={formatScore(score)} />
        <Metric label="Confidence" value={formatPct(confidence)} />
      </CardBody>
    </Card>
  );
}

export function RecommendationCard({
  decision,
  confidence,
  marginOfSafety,
}: {
  decision: string;
  confidence: number | null;
  marginOfSafety: number | null;
}) {
  return (
    <Card>
      <CardHeader
        title="Investment Recommendation"
        description="Presented as returned by /api/v1/analyse"
      />
      <CardBody className="grid gap-3 sm:grid-cols-3">
        <Metric label="Overall recommendation" value={decision} emphasize />
        <Metric label="Confidence" value={formatPct(confidence)} />
        <Metric label="Margin of safety" value={formatPct(marginOfSafety)} />
      </CardBody>
    </Card>
  );
}

export function CommitteeConsensusCard({
  decision,
  confidence,
  consensus,
  minorityNotes,
}: {
  decision: string;
  confidence: number | null;
  consensus: string | null;
  minorityNotes: string[];
}) {
  return (
    <Card>
      <CardHeader
        title="Investment Committee Consensus"
        description="Committee stage summary from the API"
      />
      <CardBody className="space-y-4">
        <div className="grid gap-3 sm:grid-cols-3">
          <Metric label="Committee decision" value={decision} emphasize />
          <Metric label="Agreement / confidence" value={formatPct(confidence)} />
          <Metric label="Consensus" value={consensus || "Unavailable"} />
        </div>
        <div>
          <h4 className="text-sm font-medium">Minority opinions / notes</h4>
          {minorityNotes.length ? (
            <ul className="mt-2 list-inside list-disc text-sm text-[var(--muted)]">
              {minorityNotes.map((n) => (
                <li key={n}>{n}</li>
              ))}
            </ul>
          ) : (
            <p className="mt-2 text-sm text-[var(--muted)]">None reported</p>
          )}
        </div>
      </CardBody>
    </Card>
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
            ? "mt-1 font-[family-name:var(--font-display)] text-2xl tracking-tight"
            : "mt-1 text-lg font-medium"
        }
      >
        {value}
      </p>
    </div>
  );
}
