"use client";

import { useMemo, useState } from "react";

import { FilterPanel } from "@/components/screening/FilterPanel";
import { ResultsSummary } from "@/components/screening/ResultsSummary";
import { ScreeningResults } from "@/components/screening/ScreeningResults";
import { PageHeader } from "@/components/layout/PageHeader";
import { COMPANY_CATALOGUE } from "@/lib/companies/catalogue";
import {
  DEFAULT_SCREENING_FILTERS,
  applyScreeningFilters,
  applyScreeningPreset,
  getFiltersAppliedCount,
  getUniqueExchanges,
  getUniqueSectors,
  type ScreeningFilters,
  type ScreeningPreset,
} from "@/lib/screening/filters";

export default function ScreeningPage() {
  const [filters, setFilters] = useState(DEFAULT_SCREENING_FILTERS);
  const [activePreset, setActivePreset] = useState<ScreeningPreset | null>(null);

  const sectors = useMemo(() => getUniqueSectors(COMPANY_CATALOGUE), []);
  const exchanges = useMemo(() => getUniqueExchanges(COMPANY_CATALOGUE), []);
  const results = useMemo(
    () => applyScreeningFilters(COMPANY_CATALOGUE, filters),
    [filters],
  );
  const filtersApplied = getFiltersAppliedCount(filters);
  const availableResearch = results.filter((company) => company.researchAvailable)
    .length;

  function updateFilter<K extends keyof ScreeningFilters>(
    key: K,
    value: ScreeningFilters[K],
  ) {
    setActivePreset(null);
    setFilters((current) => ({ ...current, [key]: value }));
  }

  function applyPreset(preset: ScreeningPreset) {
    const nextPreset = activePreset === preset ? null : preset;
    setActivePreset(nextPreset);
    setFilters((current) =>
      nextPreset === null
        ? DEFAULT_SCREENING_FILTERS
        : applyScreeningPreset(preset, current),
    );
  }

  function resetFilters() {
    setActivePreset(null);
    setFilters(DEFAULT_SCREENING_FILTERS);
  }

  return (
    <div className="space-y-8">
      <PageHeader
        title="Market Screening"
        description="Find companies using investment filters."
      />

      <FilterPanel
        filters={filters}
        sectors={sectors}
        exchanges={exchanges}
        activePreset={activePreset}
        onChange={updateFilter}
        onApplyPreset={applyPreset}
        onReset={resetFilters}
      />

      <ResultsSummary
        matched={results.length}
        filtersApplied={filtersApplied}
        availableResearch={availableResearch}
      />

      <section aria-label="Company results" className="space-y-3">
        <div>
          <h2 className="font-[family-name:var(--font-display)] text-xl tracking-tight">
            Company Results
          </h2>
          <p className="mt-0.5 text-sm text-[var(--muted)]">
            Screened locally from the featured company catalogue.
          </p>
        </div>
        <ScreeningResults companies={results} />
      </section>
    </div>
  );
}
