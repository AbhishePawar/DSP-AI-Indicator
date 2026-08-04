"use client";

/**
 * EPIC-019A — Compact trust chrome for remaining public surfaces.
 * Reuses Confidence/Source/Category badges + Research Mode banner.
 * Presentation only — no client valuation or fabricated scores.
 */

import Link from "next/link";

import { Badge } from "@/components/ds";
import { Card, CardBody, CardHeader } from "@/components/ui/Card";
import { ConfidenceBadge } from "@/components/trust/ConfidenceBadge";
import { SourceBadge } from "@/components/trust/SourceBadge";
import { ValueCategoryBadge } from "@/components/trust/ValueCategoryBadge";
import { ResearchModeBanner } from "@/components/research/ResearchModeBanner";
import type { SurfaceTrustSummary } from "@/lib/trust/surfaceTrust";
import { DATA_UNAVAILABLE } from "@/lib/trust/surfaceTrust";

function presenceTone(
  presence: "available" | "partial" | "unavailable",
): "accent" | "warning" | "outline" {
  if (presence === "available") return "accent";
  if (presence === "partial") return "warning";
  return "outline";
}

export function CompactTrustLadder({
  summary,
  title = "Trust Ladder",
}: {
  summary: SurfaceTrustSummary;
  title?: string;
}) {
  return (
    <Card data-testid="surface-trust-ladder" aria-label={title}>
      <CardHeader
        title={title}
        description="User Trust Standard — Observed Facts → Analysis → Inference → Recommendation"
      />
      <CardBody className="space-y-3">
        <div
          className="flex flex-wrap gap-2"
          aria-label="Epistemic categories"
        >
          <Badge variant="outline">Verified / Observed</Badge>
          <Badge variant="outline">Calculated</Badge>
          <Badge variant="outline">AI / Committee</Badge>
          <Badge variant="accent">Research Mode</Badge>
          <ValueCategoryBadge category="unavailable" />
          <SourceBadge source="unavailable" />
          {summary.confidenceLevel === "unavailable" ? (
            <Badge variant="outline">Confidence: {DATA_UNAVAILABLE}</Badge>
          ) : (
            <ConfidenceBadge level={summary.confidenceLevel} />
          )}
        </div>

        <p className="text-sm text-[var(--muted)]" data-testid="evidence-completeness">
          {summary.evidence.label}
          {summary.evidence.missingDataPenalty !== "none"
            ? ` · Penalty: ${summary.evidence.missingDataPenalty}`
            : null}
        </p>

        <ol className="space-y-2 text-sm">
          {summary.layers.map((layer) => (
            <li
              key={layer.id}
              className="rounded-[var(--radius-md)] border border-[var(--border)] px-3 py-2"
              data-trust-layer={layer.id}
            >
              <div className="flex flex-wrap items-center justify-between gap-2">
                <p className="text-xs font-medium uppercase tracking-wide text-[var(--muted)]">
                  {layer.title}
                </p>
                <Badge variant={presenceTone(layer.presence)}>
                  {layer.presence}
                </Badge>
              </div>
              <p className="mt-1">{layer.summary}</p>
            </li>
          ))}
        </ol>

        {summary.contradictoryEvidence.length > 0 ? (
          <div
            className="rounded-[var(--radius-md)] border border-[var(--warning-border,var(--border))] bg-[var(--warning-bg,#f7ecd2)]/40 px-3 py-2"
            data-testid="contradictory-evidence"
          >
            <p className="text-xs font-medium uppercase tracking-wide text-[var(--muted)]">
              Contradictory / opposing evidence
            </p>
            <ul className="mt-1 list-disc space-y-1 pl-5 text-sm">
              {summary.contradictoryEvidence.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          </div>
        ) : (
          <p className="text-xs text-[var(--muted)]">
            Contradictory evidence: none reported on this surface payload.
          </p>
        )}

        <div data-testid="trust-audit-trail">
          <p className="text-xs font-medium uppercase tracking-wide text-[var(--muted)]">
            Audit trail
          </p>
          <ul className="mt-1 list-disc space-y-1 pl-5 text-xs text-[var(--muted)]">
            {summary.auditTrail.map((line) => (
              <li key={line}>{line}</li>
            ))}
            <li>
              Full publish ladder:{" "}
              <Link
                href="/research/institutional"
                className="text-[var(--accent)] underline-offset-2 hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]"
              >
                Institutional Reports
              </Link>
            </li>
          </ul>
        </div>
      </CardBody>
    </Card>
  );
}

/** Page-level trust chrome: Research Mode + compact ladder. */
export function SurfaceTrustChrome({
  summary,
  title = "Trust Ladder",
  showBanner = true,
}: {
  summary: SurfaceTrustSummary;
  title?: string;
  showBanner?: boolean;
}) {
  return (
    <div className="space-y-3" data-testid="surface-trust-chrome">
      {showBanner ? <ResearchModeBanner /> : null}
      <CompactTrustLadder summary={summary} title={title} />
    </div>
  );
}
