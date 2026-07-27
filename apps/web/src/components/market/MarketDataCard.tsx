"use client";

import {
  formatChange,
  formatMarketCap,
  formatMarketPrice,
  type MarketQuote,
} from "@/lib/market";
import { Card, CardBody, CardHeader } from "@/components/ui/Card";
import { useMarketQuote } from "@/providers/MarketDataProvider";
import { LivePriceBadge } from "./LivePriceBadge";
import { LiveMarketDataLabel } from "./MarketStatusIndicator";
import { MarketStatusIndicator } from "./MarketStatusIndicator";
import { RefreshButton } from "./RefreshButton";

function formatTimestamp(iso: string | null | undefined): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleString();
}

function MetricRow({
  label,
  value,
}: {
  label: string;
  value: string;
}) {
  return (
    <div>
      <p className="text-xs text-[var(--muted)]">{label}</p>
      <p className="mt-0.5 font-mono text-sm">{value}</p>
    </div>
  );
}

export function MarketDataCard({
  ticker,
  title = "Live Market Data",
  description = "Supplemental prices — does not affect deterministic scoring",
}: {
  ticker: string;
  title?: string;
  description?: string;
}) {
  const { quote, status, refresh, isRefreshing } = useMarketQuote(ticker);

  return (
    <Card className="border-[var(--accent-soft)]">
      <CardHeader
        title={title}
        description={description}
        action={
          <div className="flex flex-wrap items-center gap-2">
            <LiveMarketDataLabel />
            <MarketStatusIndicator status={status} />
            <RefreshButton onRefresh={refresh} isRefreshing={isRefreshing} />
          </div>
        }
      />
      <CardBody>
        {quote ? (
          <MarketQuoteGrid quote={quote} />
        ) : (
          <p className="text-sm text-[var(--muted)]">
            {status === "error"
              ? "Unable to load market data for this ticker."
              : "Loading live market data…"}
          </p>
        )}
      </CardBody>
    </Card>
  );
}

export function MarketQuoteGrid({ quote }: { quote: MarketQuote }) {
  return (
    <div className="space-y-4">
      <LivePriceBadge quote={quote} />
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <MetricRow
          label="Previous Close"
          value={formatMarketPrice(quote.previousClose, quote.currency)}
        />
        <MetricRow
          label="Market Cap"
          value={formatMarketCap(quote.marketCap)}
        />
        <MetricRow
          label="Volume"
          value={
            quote.volume != null ? quote.volume.toLocaleString() : "Unavailable"
          }
        />
        <MetricRow
          label="52 Week High"
          value={formatMarketPrice(quote.week52High, quote.currency)}
        />
        <MetricRow
          label="52 Week Low"
          value={formatMarketPrice(quote.week52Low, quote.currency)}
        />
        <MetricRow
          label="Day Change"
          value={formatChange(quote.dailyChange, quote.dailyChangePercent)}
        />
        <MetricRow label="Last Updated" value={formatTimestamp(quote.lastUpdated)} />
      </div>
    </div>
  );
}
