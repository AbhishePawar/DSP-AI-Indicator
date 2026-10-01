"use client";

import Link from "next/link";

import { LivePriceBadge } from "@/components/market/LivePriceBadge";
import { Badge } from "@/components/ui/Badge";
import { Card, CardBody } from "@/components/ui/Card";
import { AddToPortfolioButton } from "@/components/portfolio/AddToPortfolioButton";
import type { CompanyEntry } from "@/lib/companies/catalogue";
import { useMarketQuote } from "@/providers/MarketDataProvider";

export function CompanyCard({ company }: { company: CompanyEntry }) {
  const { quote } = useMarketQuote(company.ticker);

  return (
    <Card data-testid={`company-card-${company.ticker}`} className="flex flex-col rounded-xl transition-colors hover:border-[var(--accent)]/40">
      <CardBody className="flex flex-1 flex-col gap-3 !px-[18px] !py-4">
        <div className="flex-1">
          <div className="flex items-start justify-between gap-3">
            <div>
              <h3 className="font-mono text-[15px] font-bold tracking-tight">{company.ticker}</h3>
              <p className="mt-1 text-xs leading-snug text-[var(--muted)]">{company.name}</p>
            </div>
            <Badge data-testid={`company-exchange-${company.ticker}`} tone="neutral" className="font-mono text-[10px]">{company.exchange}</Badge>
          </div>
          <div className="mt-4 flex items-end justify-between gap-2">
            <div data-testid={`company-price-${company.ticker}`}><LivePriceBadge quote={quote} compact /></div>
            <span className="text-right font-mono text-[10px] uppercase tracking-wide text-[var(--muted)]">{company.sector}</span>
          </div>
        </div>
        <div className="flex flex-wrap items-center justify-between gap-2 border-t border-[var(--border)] pt-3">
          <span data-testid={`company-data-status-${company.ticker}`} className="text-[10px] text-[var(--muted)]">{quote ? "Source price loaded" : "Live data unavailable"}</span>
          <div className="flex flex-wrap gap-2">
            <AddToPortfolioButton
              company={company.name}
              ticker={company.ticker}
              sector={company.sector}
              researchAvailable={false}
            />
            <Link
              data-testid={`company-research-${company.ticker}`}
              href={`/analysis?symbol=${encodeURIComponent(company.ticker)}`}
              className="inline-flex min-h-8 items-center rounded-lg border border-[var(--accent)]/20 bg-[var(--accent-soft)] px-2.5 text-[11px] text-[var(--accent)] transition-colors hover:border-[var(--accent)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]"
            >
              Research →
            </Link>
          </div>
        </div>
      </CardBody>
    </Card>
  );
}
