"use client";

import { Button } from "@/components/ui/Button";
import { usePortfolio } from "@/lib/portfolio/PortfolioProvider";

export function RemoveHoldingButton({
  ticker,
  size = "sm",
}: {
  ticker: string;
  size?: "sm" | "md";
}) {
  const { removeHolding } = usePortfolio();

  return (
    <Button
      size={size}
      variant="danger"
      onClick={() => removeHolding(ticker)}
      aria-label={`Remove ${ticker} from portfolio`}
    >
      Remove
    </Button>
  );
}
