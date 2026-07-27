"use client";

import Link from "next/link";

import { LivePriceBadge } from "@/components/market/LivePriceBadge";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Td, Tr } from "@/components/ui/Table";
import type { PortfolioHolding } from "@/lib/portfolio/model";
import { useMarketQuote } from "@/providers/MarketDataProvider";
import { RemoveHoldingButton } from "./RemoveHoldingButton";

export function HoldingRow({ holding }: { holding: PortfolioHolding }) {
  const { quote } = useMarketQuote(holding.ticker);

  return (
    <Tr>
      <Td>{holding.company}</Td>
      <Td>
        <span className="font-mono text-xs">{holding.ticker}</span>
      </Td>
      <Td>{holding.sector}</Td>
      <Td>{holding.allocationPercent.toFixed(1)}%</Td>
      <Td>
        <LivePriceBadge quote={quote} compact />
      </Td>
      <Td>{holding.recommendation}</Td>
      <Td>
        <Badge tone={holding.researchAvailable ? "success" : "neutral"}>
          {holding.researchAvailable ? "Yes" : "No"}
        </Badge>
      </Td>
      <Td>
        <div className="flex flex-wrap gap-2">
          <Link href={`/research/${encodeURIComponent(holding.ticker)}`}>
            <Button size="sm" variant="secondary">
              Open Research
            </Button>
          </Link>
          <RemoveHoldingButton ticker={holding.ticker} />
        </div>
      </Td>
    </Tr>
  );
}
