"use client";

import { Card, CardBody } from "@/components/ui/Card";

export function CompanyStats({
  total,
  researchAvailable,
  featured,
  recentlyAnalysed,
}: {
  total: number;
  researchAvailable: number;
  featured: number;
  recentlyAnalysed: number;
}) {
  return (
    <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
      <StatCard label="Total Companies" value={total} />
      <StatCard label="Research Available" value={researchAvailable} />
      <StatCard label="Featured Companies" value={featured} />
      <StatCard label="Recently Analysed" value={recentlyAnalysed} />
    </div>
  );
}

function StatCard({ label, value }: { label: string; value: number }) {
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
