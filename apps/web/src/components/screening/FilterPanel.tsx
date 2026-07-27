"use client";

import { Card, CardBody, CardHeader } from "@/components/ui/Card";
import { Input } from "@/components/ui/Input";
import {
  SCREENING_PRESETS,
  type ScreeningFilters,
  type ScreeningPreset,
} from "@/lib/screening/filters";
import { FilterChip } from "./FilterChip";
import { FilterGroup } from "./FilterGroup";

function Select({
  value,
  onChange,
  options,
  ariaLabel,
}: {
  value: string;
  onChange: (value: string) => void;
  options: string[];
  ariaLabel: string;
}) {
  return (
    <select
      value={value}
      onChange={(event) => onChange(event.target.value)}
      aria-label={ariaLabel}
      className="w-full rounded-md border border-[var(--border)] bg-[var(--bg)] px-3 py-2 text-sm text-[var(--fg)] outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]"
    >
      {options.map((option) => (
        <option key={option} value={option}>
          {option === "all" ? "All" : option}
        </option>
      ))}
    </select>
  );
}

export function FilterPanel({
  filters,
  sectors,
  exchanges,
  activePreset,
  onChange,
  onApplyPreset,
  onReset,
}: {
  filters: ScreeningFilters;
  sectors: string[];
  exchanges: string[];
  activePreset: ScreeningPreset | null;
  onChange: <K extends keyof ScreeningFilters>(
    key: K,
    value: ScreeningFilters[K],
  ) => void;
  onApplyPreset: (preset: ScreeningPreset) => void;
  onReset: () => void;
}) {
  return (
    <Card>
      <CardHeader
        title="Filter Panel"
        description="Client-side filter framework over the local company catalogue"
      />
      <CardBody className="space-y-5">
        <div className="space-y-3">
          <p className="text-xs font-medium uppercase tracking-wider text-[var(--muted)]">
            Quick Filters
          </p>
          <div className="flex flex-wrap gap-2">
            {SCREENING_PRESETS.map((preset) => (
              <FilterChip
                key={preset.id}
                label={preset.label}
                active={activePreset === preset.id}
                onClick={() => onApplyPreset(preset.id)}
              />
            ))}
            <FilterChip
              label="Reset"
              active={false}
              onClick={onReset}
            />
          </div>
        </div>

        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          <FilterGroup label="Search">
            <Input
              value={filters.query}
              onChange={(event) => onChange("query", event.target.value)}
              placeholder="Company name or ticker"
              aria-label="Search screening companies"
            />
          </FilterGroup>

          <FilterGroup label="ROE Min %">
            <Input
              value={filters.minRoe}
              onChange={(event) => onChange("minRoe", event.target.value)}
              inputMode="decimal"
              placeholder="e.g. 20"
              aria-label="Minimum ROE"
            />
          </FilterGroup>

          <FilterGroup label="ROCE Min %">
            <Input
              value={filters.minRoce}
              onChange={(event) => onChange("minRoce", event.target.value)}
              inputMode="decimal"
              placeholder="e.g. 20"
              aria-label="Minimum ROCE"
            />
          </FilterGroup>

          <FilterGroup label="Debt to Equity Max">
            <Input
              value={filters.maxDebtToEquity}
              onChange={(event) =>
                onChange("maxDebtToEquity", event.target.value)
              }
              inputMode="decimal"
              placeholder="e.g. 0.5"
              aria-label="Maximum debt to equity"
            />
          </FilterGroup>

          <FilterGroup label="Revenue Growth Min %">
            <Input
              value={filters.minRevenueGrowth}
              onChange={(event) =>
                onChange("minRevenueGrowth", event.target.value)
              }
              inputMode="decimal"
              placeholder="e.g. 12"
              aria-label="Minimum revenue growth"
            />
          </FilterGroup>

          <FilterGroup label="Profit Growth Min %">
            <Input
              value={filters.minProfitGrowth}
              onChange={(event) =>
                onChange("minProfitGrowth", event.target.value)
              }
              inputMode="decimal"
              placeholder="e.g. 12"
              aria-label="Minimum profit growth"
            />
          </FilterGroup>

          <FilterGroup label="Market Cap">
            <Select
              value={filters.marketCap}
              onChange={(value) => onChange("marketCap", value as ScreeningFilters["marketCap"])}
              options={["all", "large", "mid", "small"]}
              ariaLabel="Market cap filter"
            />
          </FilterGroup>

          <FilterGroup label="Sector">
            <Select
              value={filters.sector}
              onChange={(value) => onChange("sector", value)}
              options={["all", ...sectors]}
              ariaLabel="Sector filter"
            />
          </FilterGroup>

          <FilterGroup label="Exchange">
            <Select
              value={filters.exchange}
              onChange={(value) => onChange("exchange", value)}
              options={["all", ...exchanges]}
              ariaLabel="Exchange filter"
            />
          </FilterGroup>

          <FilterGroup label="Research Available">
            <Select
              value={filters.researchAvailable}
              onChange={(value) =>
                onChange(
                  "researchAvailable",
                  value as ScreeningFilters["researchAvailable"],
                )
              }
              options={["all", "yes", "no"]}
              ariaLabel="Research availability filter"
            />
          </FilterGroup>

          <FilterGroup label="Dividend">
            <Select
              value={filters.dividend}
              onChange={(value) =>
                onChange("dividend", value as ScreeningFilters["dividend"])
              }
              options={["all", "yes", "no"]}
              ariaLabel="Dividend filter"
            />
          </FilterGroup>

          <FilterGroup label="Style">
            <Select
              value={filters.style}
              onChange={(value) =>
                onChange("style", value as ScreeningFilters["style"])
              }
              options={["all", "growth", "value", "blend"]}
              ariaLabel="Style filter"
            />
          </FilterGroup>
        </div>
      </CardBody>
    </Card>
  );
}
