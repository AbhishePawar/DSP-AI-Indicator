"use client";

import { Button } from "@/components/ui/Button";
import { usePortfolio } from "@/lib/portfolio/PortfolioProvider";
import type { AddHoldingInput } from "@/lib/portfolio/model";

export function AddToPortfolioButton({
  company,
  ticker,
  sector,
  recommendation,
  researchAvailable = true,
  size = "sm",
}: AddHoldingInput & {
  size?: "sm" | "md";
}) {
  const { hasTicker, addHolding } = usePortfolio();
  const inPortfolio = hasTicker(ticker);

  return (
    <Button
      size={size}
      variant={inPortfolio ? "ghost" : "secondary"}
      disabled={inPortfolio}
      aria-pressed={inPortfolio}
      onClick={() =>
        addHolding({
          company,
          ticker,
          sector,
          recommendation,
          researchAvailable,
        })
      }
    >
      {inPortfolio ? "In Portfolio" : "Add to Portfolio"}
    </Button>
  );
}
