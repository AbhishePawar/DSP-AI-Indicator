"use client";

/**
 * EPIC-015 — Portfolio Intelligence 2.0 presentation sections.
 * Honest unavailable when API fields are absent. Never recommend transactions.
 */

import Link from "next/link";

import { Button } from "@/components/ds";
import { featureFlags } from "@/lib/featureFlags";
import type { PortfolioIntelligenceView } from "@/lib/portfolio-intelligence";
import type { PortfolioActivity, PortfolioHolding } from "@/lib/portfolio/model";
import {
  FieldRow,
  SectionCard,
  WorkspaceEmpty,
} from "./Primitives";

export function ScenariosSection({
  intel,
}: {
  intel: PortfolioIntelligenceView | null;
}) {
  return (
    <div className="space-y-4">
      <SectionCard
        title="Portfolio Scenarios"
        description="Bull / Base / Bear require authenticated portfolio scenario feeds — never invented client-side"
      >
        <dl>
          <FieldRow label="Bull case" value="Analysis unavailable." />
          <FieldRow label="Base case" value="Analysis unavailable." />
          <FieldRow label="Bear case" value="Analysis unavailable." />
          <FieldRow
            label="Intelligence schema"
            value={intel?.schemaVersion ?? "Data unavailable."}
          />
        </dl>
        <p className="mt-3 text-xs text-[var(--muted)]">
          Scenario labels are placeholders for future API fields. No fabricated
          portfolio returns or probability weights.
        </p>
      </SectionCard>
    </div>
  );
}

export function DriftSection({
  intel,
  holdings,
}: {
  intel: PortfolioIntelligenceView | null;
  holdings: PortfolioHolding[];
}) {
  return (
    <div className="space-y-4">
      <SectionCard
        title="Allocation Drift"
        description="Drift vs policy / target requires backend feeds"
      >
        <dl>
          <FieldRow
            label="Holdings in session"
            value={holdings.length || "Data unavailable."}
          />
          <FieldRow
            label="Sector concentration note"
            value={intel?.concentrationNote ?? "Data unavailable."}
          />
          <FieldRow label="Target drift %" value="Data unavailable." />
          <FieldRow label="Policy benchmark" value="Data unavailable." />
        </dl>
        <WorkspaceEmpty description="Data unavailable. No portfolio drift API field in the frozen client. Session sector counts appear under Allocation when present." />
      </SectionCard>
    </div>
  );
}

export function PortfolioTimelineSection({
  activities,
  holdings,
}: {
  activities: PortfolioActivity[];
  holdings: PortfolioHolding[];
}) {
  return (
    <div className="space-y-4">
      <SectionCard
        title="Portfolio Timeline"
        description="Session activity only — immutable local history when recorded"
      >
        {activities.length === 0 ? (
          <WorkspaceEmpty description="Data unavailable. Portfolio activity appears as holdings change in this session." />
        ) : (
          <ul className="space-y-2 text-sm">
            {activities.slice(0, 20).map((a) => (
              <li key={a.id} className="flex justify-between gap-3">
                <span>{a.label}</span>
                <span className="text-xs text-[var(--muted)]">
                  {new Date(a.timestamp).toLocaleString()}
                </span>
              </li>
            ))}
          </ul>
        )}
      </SectionCard>
      <SectionCard title="Coverage events">
        <p className="text-sm text-[var(--muted)]">
          {holdings.filter((h) => h.researchAvailable).length} holding(s) marked
          research-available in session · remainder Data unavailable until
          linked via /portfolio/intelligence.
        </p>
      </SectionCard>
    </div>
  );
}

export function IntegrationsSection({
  holdings,
}: {
  holdings: PortfolioHolding[];
}) {
  const first = holdings[0]?.ticker;
  return (
    <div className="space-y-4">
      <SectionCard
        title="Research integrations"
        description="Links into existing institutional surfaces — no parallel product"
      >
        <div className="flex flex-wrap gap-2">
          <Link
            href={
              first
                ? `/analysis?symbol=${encodeURIComponent(first)}`
                : "/analysis"
            }
          >
            <Button size="sm" variant="secondary">
              Company Research
            </Button>
          </Link>
          {featureFlags.companyComparison ? (
            <Link
              href={
                holdings.length >= 2
                  ? `/analysis/compare?symbols=${encodeURIComponent(
                      holdings
                        .slice(0, 5)
                        .map((h) => h.ticker)
                        .join(","),
                    )}`
                  : "/analysis/compare"
              }
            >
              <Button size="sm" variant="secondary">
                Comparison
              </Button>
            </Link>
          ) : null}
          {featureFlags.researchIntelligence ? (
            <Link href="/research/intelligence">
              <Button size="sm" variant="secondary">
                Research Intelligence
              </Button>
            </Link>
          ) : null}
          <Link
            href={
              first
                ? `/analysis?symbol=${encodeURIComponent(first)}&section=evidence`
                : "/analysis?section=evidence"
            }
          >
            <Button size="sm" variant="ghost">
              Evidence
            </Button>
          </Link>
          <Link
            href={
              first
                ? `/analysis?symbol=${encodeURIComponent(first)}&section=ai`
                : "/analysis?section=ai"
            }
          >
            <Button size="sm" variant="ghost">
              Committee
            </Button>
          </Link>
          {featureFlags.researchCanvas ? (
            <Link
              href={
                first
                  ? `/research/canvas?symbol=${encodeURIComponent(first)}`
                  : "/research/canvas"
              }
            >
              <Button size="sm" variant="ghost">
                Research Canvas
              </Button>
            </Link>
          ) : null}
        </div>
      </SectionCard>
      <SectionCard title="Rebalancing honesty">
        <p className="text-sm text-[var(--muted)]">
          Rebalancing suggestions remain trade-off / evidence / confidence review
          only. This workspace never recommends transactions or personalized
          investment advice.
        </p>
      </SectionCard>
    </div>
  );
}

export function OverviewV2Extras({
  holdings,
  intel,
}: {
  holdings: PortfolioHolding[];
  intel: PortfolioIntelligenceView | null;
}) {
  if (!featureFlags.portfolioIntelligenceV2) return null;

  const sectors = new Map<string, number>();
  for (const h of holdings) {
    const key = h.sector || "Unknown";
    sectors.set(key, (sectors.get(key) ?? 0) + 1);
  }

  return (
    <SectionCard
      title="Allocation overview (session counts)"
      description="EPIC-015 — value / country / cash allocation require API fields; counts only when present"
    >
      <dl>
        <FieldRow
          label="Portfolio value"
          value="Data unavailable. No portfolio market-value API in session."
        />
        <FieldRow
          label="Sector allocation"
          value={
            sectors.size
              ? Array.from(sectors.entries())
                  .map(([s, n]) => `${s}: ${n}`)
                  .join(" · ")
              : "Data unavailable."
          }
        />
        <FieldRow
          label="Industry allocation"
          value="Data unavailable. Industry not on session holding model."
        />
        <FieldRow
          label="Market-cap allocation"
          value="Data unavailable."
        />
        <FieldRow label="Country allocation" value="Data unavailable." />
        <FieldRow label="Cash allocation" value="Data unavailable." />
        <FieldRow
          label="API unique sectors"
          value={intel?.uniqueSectorCount ?? "Data unavailable."}
        />
      </dl>
    </SectionCard>
  );
}
