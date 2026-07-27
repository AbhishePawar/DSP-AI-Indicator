"use client";

import {
  formatChange,
  formatMarketPrice,
  type MarketQuote,
} from "@/lib/market";
import { Badge } from "@/components/ui/Badge";

export function LivePriceBadge({
  quote,
  compact = false,
}: {
  quote: MarketQuote | null;
  compact?: boolean;
}) {
  if (!quote) {
    return (
      <Badge tone="neutral" className="font-mono">
        Price —
      </Badge>
    );
  }

  const positive = quote.dailyChange >= 0;
  const tone = positive ? "success" : "danger";

  if (compact) {
    return (
      <span className="inline-flex items-center gap-2 font-mono text-xs">
        <span>{formatMarketPrice(quote.currentPrice, quote.currency)}</span>
        <Badge tone={tone}>
          {formatChange(quote.dailyChange, quote.dailyChangePercent)}
        </Badge>
      </span>
    );
  }

  return (
    <div className="flex flex-wrap items-center gap-2">
      <span className="font-mono text-sm font-medium">
        {formatMarketPrice(quote.currentPrice, quote.currency)}
      </span>
      <Badge tone={tone}>
        {formatChange(quote.dailyChange, quote.dailyChangePercent)}
      </Badge>
    </div>
  );
}
