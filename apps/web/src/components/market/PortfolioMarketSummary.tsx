"use client";

import { useMemo } from "react";

import { Card, CardBody, CardHeader } from "@/components/ui/Card";
import {
  buildPortfolioMarketSummary,
  formatChange,
  formatMarketPrice,
} from "@/lib/market";
import type { PortfolioHolding } from "@/lib/portfolio/model";
import { useMarketQuotes } from "@/providers/MarketDataProvider";
import { LiveMarketDataLabel } from "./MarketStatusIndicator";
import { MarketStatusIndicator } from "./MarketStatusIndicator";
import { RefreshButton } from "./RefreshButton";

export function PortfolioMarketSummary({
  holdings,
}: {
  holdings: PortfolioHolding[];
}) {
  const tickers = useMemo(
    () => holdings.map((h) => h.ticker),
    [holdings],
  );
  const { quotes, status, refresh, isRefreshing, lastUpdated } =
    useMarketQuotes(tickers);

  const summary = useMemo(
    () => buildPortfolioMarketSummary(holdings, quotes),
    [holdings, quotes],
  );

  if (!holdings.length) return null;

  const dayTone =
    summary.dayChange != null && summary.dayChange >= 0 ? "text-[var(--accent)]" : "text-[var(--danger-fg)]";

  return (
    <Card className="border-[var(--accent-soft)]">
      <CardHeader
        title="Live Portfolio Value"
        description="Presentation-layer market values — portfolio analytics remain deterministic"
        action={
          <div className="flex flex-wrap items-center gap-2">
            <LiveMarketDataLabel />
            <MarketStatusIndicator status={status} />
            <RefreshButton onRefresh={refresh} isRefreshing={isRefreshing} />
          </div>
        }
      />
      <CardBody>
        <div className="grid gap-4 sm:grid-cols-3">
          <div>
            <p className="text-xs text-[var(--muted)]">Total Value</p>
            <p className="mt-1 font-[family-name:var(--font-display)] text-2xl tracking-tight">
              {formatMarketPrice(summary.totalValue)}
            </p>
          </div>
          <div>
            <p className="text-xs text-[var(--muted)]">Portfolio Day Change</p>
            <p className={`mt-1 font-mono text-lg ${dayTone}`}>
              {formatChange(summary.dayChange, summary.dayChangePercent)}
            </p>
          </div>
          <div>
            <p className="text-xs text-[var(--muted)]">Last Updated</p>
            <p className="mt-1 font-mono text-sm">
              {lastUpdated
                ? new Date(lastUpdated).toLocaleString()
                : "—"}
            </p>
          </div>
        </div>
      </CardBody>
    </Card>
  );
}
