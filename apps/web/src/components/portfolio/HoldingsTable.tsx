"use client";

import { Card, CardBody, CardHeader } from "@/components/ui/Card";
import { Table } from "@/components/ui/Table";
import type { PortfolioHolding } from "@/lib/portfolio/model";
import { HoldingRow } from "./HoldingRow";

const HEADERS = [
  "Company",
  "Ticker",
  "Sector",
  "Allocation %",
  "Live Price",
  "Recommendation",
  "Research Available",
  "Action",
];

export function HoldingsTable({ holdings }: { holdings: PortfolioHolding[] }) {
  return (
    <Card>
      <CardHeader title="Holdings" description="Placeholder session holdings" />
      <CardBody>
        <Table headers={HEADERS} caption="Portfolio holdings">
          {holdings.map((holding) => (
            <HoldingRow key={holding.ticker} holding={holding} />
          ))}
        </Table>
      </CardBody>
    </Card>
  );
}
