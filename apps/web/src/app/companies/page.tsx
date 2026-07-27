"use client";

import { useMemo, useState } from "react";

import { PageHeader } from "@/components/layout/PageHeader";
import { CompanyCategory } from "@/components/companies/CompanyCategory";
import { CompanyGrid } from "@/components/companies/CompanyGrid";
import { CompanySearch } from "@/components/companies/CompanySearch";
import { CompanyStats } from "@/components/companies/CompanyStats";
import {
  getCatalogueStats,
  getFeaturedCompanies,
  searchCatalogue,
} from "@/lib/companies/catalogue";

export default function CompaniesPage() {
  const [query, setQuery] = useState("");
  const stats = getCatalogueStats();
  const featured = getFeaturedCompanies();
  const results = useMemo(() => searchCatalogue(query), [query]);
  const isSearching = query.trim().length > 0;

  return (
    <div className="space-y-8">
      <PageHeader
        title="Company Directory"
        description={`Browse companies and open detailed investment research. ${stats.total} companies available.`}
      />

      <CompanySearch value={query} onChange={setQuery} />

      <CompanyStats {...stats} />

      {isSearching ? (
        <section aria-label="Search results">
          <h2 className="mb-3 font-[family-name:var(--font-display)] text-xl tracking-tight">
            Search Results
          </h2>
          <CompanyGrid companies={results} />
        </section>
      ) : (
        <div className="space-y-8">
          <CompanyCategory
            title="Featured Companies"
            description="Curated list of major companies with research available"
            companies={featured}
          />
          <CompanyCategory
            title="Recently Analysed"
            description="Companies analysed in the current session"
            placeholder="Run an analysis in the Intelligence Workspace to see results here."
          />
          <CompanyCategory
            title="Popular Companies"
            description="Most frequently researched"
            placeholder="Usage statistics will appear here in a future release."
          />
          <CompanyCategory
            title="Bookmarks"
            description="Your saved companies"
            placeholder="Bookmarking coming in a future epic."
          />
          <CompanyCategory
            title="Watchlist"
            description="Companies you are tracking"
            placeholder="Watchlist feature coming in a future epic."
          />
        </div>
      )}
    </div>
  );
}
