"use client";

import type { CompanyEntry } from "@/lib/companies/catalogue";
import { NoSearchResultsEmpty } from "@/components/ui/StandardEmptyStates";
import { CompanyCard } from "./CompanyCard";

export function CompanyGrid({ companies }: { companies: CompanyEntry[] }) {
  if (companies.length === 0) {
    return <NoSearchResultsEmpty />;
  }

  return (
    <div data-testid="company-grid" className="grid grid-cols-[repeat(auto-fill,minmax(min(100%,280px),1fr))] gap-3">
      {companies.map((c) => (
        <CompanyCard key={c.ticker} company={c} />
      ))}
    </div>
  );
}
