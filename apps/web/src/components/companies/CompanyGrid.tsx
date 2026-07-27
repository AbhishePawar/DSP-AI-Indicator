"use client";

import type { CompanyEntry } from "@/lib/companies/catalogue";
import { NoSearchResultsEmpty } from "@/components/ui/StandardEmptyStates";
import { CompanyCard } from "./CompanyCard";

export function CompanyGrid({ companies }: { companies: CompanyEntry[] }) {
  if (companies.length === 0) {
    return <NoSearchResultsEmpty />;
  }

  return (
    <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
      {companies.map((c) => (
        <CompanyCard key={c.ticker} company={c} />
      ))}
    </div>
  );
}
