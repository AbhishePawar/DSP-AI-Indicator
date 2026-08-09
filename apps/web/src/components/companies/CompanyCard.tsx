"use client";

import Link from "next/link";

import { LivePriceBadge } from "@/components/market/LivePriceBadge";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card, CardBody } from "@/components/ui/Card";
import { AddToPortfolioButton } from "@/components/portfolio/AddToPortfolioButton";
import type { CompanyEntry } from "@/lib/companies/catalogue";
import { useMarketQuote } from "@/providers/MarketDataProvider";

export function CompanyCard({ company }: { company: CompanyEntry }) {
  const { quote } = useMarketQuote(company.ticker);

  return (
    <Card className="flex flex-col">
      <CardBody className="flex flex-1 flex-col gap-3">
        <div className="flex-1">
          <h3 className="font-[family-name:var(--font-display)] text-lg tracking-tight">
            {company.name}
          </h3>
          <p className="mt-0.5 font-mono text-sm text-[var(--muted)]">
            {company.ticker} · {company.exchange}
          </p>
          <p className="mt-2 text-xs text-[var(--muted)]">
            {company.sector} — {company.industry}
          </p>
          <div className="mt-3">
            <LivePriceBadge quote={quote} compact />
          </div>
        </div>
        <div className="flex flex-wrap items-center justify-between gap-2">
          <Badge tone={company.researchAvailable ? "success" : "neutral"}>
            {company.researchAvailable ? "Research available" : "Pending"}
          </Badge>
          <div className="flex flex-wrap gap-2">
            <AddToPortfolioButton
              company={company.name}
              ticker={company.ticker}
              sector={company.sector}
              researchAvailable={company.researchAvailable}
            />
            <Link
              href={`/analysis?symbol=${encodeURIComponent(company.ticker)}`}
            >
              <Button size="sm" variant="secondary">
                Open Research
              </Button>
            </Link>
          </div>
        </div>
      </CardBody>
    </Card>
  );
}
