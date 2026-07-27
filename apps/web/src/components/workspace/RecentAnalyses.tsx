"use client";

import Link from "next/link";

import { Button } from "@/components/ui/Button";
import { Card, CardBody, CardHeader } from "@/components/ui/Card";
import type { RecentAnalysisEntry } from "@/lib/analysis/recentAnalyses";

export function RecentAnalyses({
  items,
  onSelect,
}: {
  items: RecentAnalysisEntry[];
  onSelect?: (entry: RecentAnalysisEntry) => void;
}) {
  return (
    <Card>
      <CardHeader
        title="Recent Analyses"
        description="Session only — cleared when the tab closes"
      />
      <CardBody>
        {items.length === 0 ? (
          <p className="text-sm text-[var(--muted)]">No analyses yet this session.</p>
        ) : (
          <ul className="space-y-3" aria-label="Recent analyses">
            {items.map((item) => (
              <li
                key={`${item.ticker}-${item.analysedAt}`}
                className="flex flex-wrap items-center justify-between gap-2 border-b border-[var(--border)] pb-3 last:border-0 last:pb-0"
              >
                <div className="min-w-0">
                  <p className="text-sm font-medium">
                    {item.company}{" "}
                    <span className="font-mono text-xs text-[var(--muted)]">
                      {item.ticker}
                    </span>
                  </p>
                  <p className="mt-0.5 text-xs text-[var(--muted)]">
                    {new Date(item.analysedAt).toLocaleString()} ·{" "}
                    {item.recommendation}
                  </p>
                </div>
                <div className="flex flex-wrap gap-2">
                  {onSelect ? (
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => onSelect(item)}
                    >
                      Re-run
                    </Button>
                  ) : null}
                  <Link href={`/research/${encodeURIComponent(item.ticker)}`}>
                    <Button size="sm" variant="secondary">
                      Open Research
                    </Button>
                  </Link>
                </div>
              </li>
            ))}
          </ul>
        )}
      </CardBody>
    </Card>
  );
}
