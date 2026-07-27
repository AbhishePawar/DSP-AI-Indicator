"use client";

import type { MarketDataStatus } from "@/lib/market";
import { Badge } from "@/components/ui/Badge";

const LABELS: Record<MarketDataStatus, string> = {
  idle: "Market idle",
  loading: "Loading market data",
  success: "Live market data",
  stale: "Stale market data",
  error: "Market data error",
};

const TONES: Record<
  MarketDataStatus,
  "neutral" | "success" | "warning" | "danger" | "accent"
> = {
  idle: "neutral",
  loading: "accent",
  success: "success",
  stale: "warning",
  error: "danger",
};

export function MarketStatusIndicator({
  status,
  className = "",
}: {
  status: MarketDataStatus;
  className?: string;
}) {
  return (
    <Badge tone={TONES[status]} className={className}>
      {LABELS[status]}
    </Badge>
  );
}

export function LiveMarketDataLabel({ className = "" }: { className?: string }) {
  return (
    <Badge tone="accent" className={className}>
      Live Market Data
    </Badge>
  );
}

export function DeterministicAnalysisLabel({
  className = "",
}: {
  className?: string;
}) {
  return (
    <Badge tone="neutral" className={className}>
      Deterministic Analysis
    </Badge>
  );
}
