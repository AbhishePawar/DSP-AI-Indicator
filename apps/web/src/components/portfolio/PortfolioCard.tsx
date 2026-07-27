"use client";

import { Card, CardBody } from "@/components/ui/Card";

export function PortfolioCard({
  label,
  value,
}: {
  label: string;
  value: string | number;
}) {
  return (
    <Card>
      <CardBody>
        <p className="text-xs text-[var(--muted)]">{label}</p>
        <p className="mt-1 font-[family-name:var(--font-display)] text-2xl tracking-tight">
          {value}
        </p>
      </CardBody>
    </Card>
  );
}
