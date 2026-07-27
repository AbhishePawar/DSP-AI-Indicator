"use client";

import Link from "next/link";

import { Button } from "@/components/ui/Button";
import { Card, CardBody, CardHeader } from "@/components/ui/Card";
import { usePortfolio } from "@/lib/portfolio/PortfolioProvider";

export function PortfolioActions() {
  const { isEmpty, loadDemo, clearPortfolio } = usePortfolio();

  return (
    <Card>
      <CardHeader title="Quick Actions" />
      <CardBody className="flex flex-wrap gap-3">
        <Link href="/companies">
          <Button variant="secondary">Browse Companies</Button>
        </Link>
        <Link href="/screening">
          <Button variant="secondary">Open Screening</Button>
        </Link>
        {isEmpty ? (
          <Button variant="secondary" onClick={loadDemo}>
            Load Demo Holdings
          </Button>
        ) : (
          <Button variant="ghost" onClick={clearPortfolio}>
            Clear Portfolio
          </Button>
        )}
        <Button variant="ghost" disabled title="Coming in a future epic">
          Create Watchlist
        </Button>
      </CardBody>
    </Card>
  );
}
