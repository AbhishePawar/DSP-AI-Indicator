"use client";

import { useState } from "react";

import { PageHeader } from "@/components/layout/PageHeader";
import { CompanyGrid } from "@/components/companies/CompanyGrid";
import { CompanySearch } from "@/components/companies/CompanySearch";
import { COMPANY_CATALOGUE, searchCatalogue } from "@/lib/companies/catalogue";

export default function CompaniesPage() {
  const [query, setQuery] = useState("");
  const [sector, setSector] = useState("all");
  const sectors = [...new Set(COMPANY_CATALOGUE.map((company) => company.sector))].sort();
  const results = searchCatalogue(query).filter((company) => sector === "all" || company.sector === sector);

  return (
    <div data-testid="company-directory" className="space-y-4">
      <PageHeader title="Company Directory" description="Discover and search listed securities" />
      <div className="flex flex-wrap items-center gap-2.5">
        <div className="min-w-0 flex-1 basis-60"><CompanySearch value={query} onChange={setQuery} /></div>
        <select data-testid="company-directory-sector" aria-label="Filter by sector" value={sector} onChange={(event) => setSector(event.target.value)} className="min-h-10 max-w-full rounded-lg border border-[var(--border)] bg-[var(--surface)] px-3 font-mono text-xs outline-none focus:border-[var(--accent)]">
          <option value="all">All Sectors</option>
          {sectors.map((value) => <option key={value} value={value}>{value}</option>)}
        </select>
        <span data-testid="company-directory-count" aria-live="polite" className="font-mono text-xs text-[var(--muted)]">{results.length} results</span>
      </div>
      <CompanyGrid companies={results} />
      <p data-testid="company-directory-data-note" className="text-[11px] leading-relaxed text-[var(--muted)]">Reference company directory. Prices and research are shown only when verified source data is available; directory inclusion does not imply research coverage.</p>
    </div>
  );
}
