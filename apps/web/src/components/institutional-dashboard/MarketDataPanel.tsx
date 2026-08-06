import { MetricCell } from "@/components/institutional-dashboard/MetricCell";
import { SectionShell } from "@/components/institutional-dashboard/SectionShell";
import { Alert } from "@/components/ds";
import type { MarketDataView } from "@/lib/institutional-dashboard/types";

export function MarketDataPanel({ view }: { view: MarketDataView }) {
  return (
    <SectionShell
      id="rs-002-market"
      title="Authenticated Market Data"
      description="RS-002 — exchange / approved provider only; never invent quotes"
    >
      {!view.hasAuthenticatedMarketData ? (
        <Alert variant="warning">
          Authenticated market-data feed is not attached to this composition
          contract. Fields show Data unavailable. — no estimated or placeholder
          quotes.
        </Alert>
      ) : null}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
        <MetricCell label="Current price" field={view.currentPrice} />
        <MetricCell label="Open" field={view.open} />
        <MetricCell label="High" field={view.high} />
        <MetricCell label="Low" field={view.low} />
        <MetricCell label="Previous close" field={view.previousClose} />
        <MetricCell label="52 week high" field={view.week52High} />
        <MetricCell label="52 week low" field={view.week52Low} />
        <MetricCell label="Volume" field={view.volume} />
        <MetricCell label="Average volume" field={view.averageVolume} />
        <MetricCell label="Market capitalisation" field={view.marketCap} />
        <MetricCell label="Enterprise value" field={view.enterpriseValue} />
        <MetricCell label="Dividend yield" field={view.dividendYield} />
        <MetricCell label="Shares outstanding" field={view.sharesOutstanding} />
        <MetricCell label="Beta" field={view.beta} />
        <MetricCell label="Timestamp" field={view.timestamp} />
        <MetricCell label="Data source" field={view.source} />
      </div>
    </SectionShell>
  );
}
