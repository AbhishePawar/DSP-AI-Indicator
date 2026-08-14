"use client";

/**
 * Portfolio Intelligence Analytics — benchmark selector.
 *
 * Activates the already-built, already-tested backend benchmark support
 * (Beta, Jensen's Alpha, Treynor Ratio, Tracking Error, Information Ratio
 * in `portfolio_analytics.performance`; beta-implied Stress Testing shocks
 * in `portfolio_analytics.stress`) — those endpoints have always accepted
 * a `benchmark_symbol`, but the workspace never collected one from the
 * user, so those five metrics were always "Data unavailable." in
 * production. No new backend logic; this is UI wiring only.
 */

import { useId, useState } from "react";

import { Button, Input } from "@/components/ds";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ds";
import {
  BENCHMARK_PRESETS,
  usePortfolioIntelPrefsStore,
} from "@/lib/portfolio-intelligence";

const CUSTOM_VALUE = "__custom__";
const NONE_VALUE = "__none__";

export function BenchmarkSelector() {
  const benchmarkSymbol = usePortfolioIntelPrefsStore((s) => s.benchmarkSymbol);
  const setBenchmarkSymbol = usePortfolioIntelPrefsStore(
    (s) => s.setBenchmarkSymbol,
  );
  const isPreset = BENCHMARK_PRESETS.some((p) => p.symbol === benchmarkSymbol);
  const [customMode, setCustomMode] = useState(
    Boolean(benchmarkSymbol) && !isPreset,
  );
  const [customValue, setCustomValue] = useState(benchmarkSymbol ?? "");
  const inputId = useId();

  function handlePresetChange(value: string) {
    if (value === NONE_VALUE) {
      setCustomMode(false);
      setBenchmarkSymbol(null);
      return;
    }
    if (value === CUSTOM_VALUE) {
      setCustomMode(true);
      return;
    }
    setCustomMode(false);
    setBenchmarkSymbol(value);
  }

  function applyCustom() {
    setBenchmarkSymbol(customValue || null);
  }

  return (
    <div className="flex flex-wrap items-center gap-2" aria-label="Benchmark selection">
      <label
        htmlFor={inputId}
        className="text-xs font-medium text-[var(--muted)]"
      >
        Benchmark
      </label>
      <Select
        value={customMode ? CUSTOM_VALUE : benchmarkSymbol ?? NONE_VALUE}
        onValueChange={handlePresetChange}
      >
        <SelectTrigger id={inputId} className="h-9 w-[200px]">
          <SelectValue placeholder="No benchmark" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value={NONE_VALUE}>No benchmark</SelectItem>
          {BENCHMARK_PRESETS.map((preset) => (
            <SelectItem key={preset.symbol} value={preset.symbol}>
              {preset.label}
            </SelectItem>
          ))}
          <SelectItem value={CUSTOM_VALUE}>Custom symbol…</SelectItem>
        </SelectContent>
      </Select>
      {customMode ? (
        <form
          className="flex items-center gap-2"
          onSubmit={(e) => {
            e.preventDefault();
            applyCustom();
          }}
        >
          <Input
            aria-label="Custom benchmark symbol"
            placeholder="e.g. VTI"
            value={customValue}
            onChange={(e) => setCustomValue(e.target.value)}
            className="h-9 w-28"
          />
          <Button size="sm" type="submit" variant="secondary">
            Apply
          </Button>
        </form>
      ) : null}
      <p className="text-[10px] text-[var(--muted)]">
        {benchmarkSymbol
          ? `Beta/Alpha/Treynor/Tracking Error/Information Ratio computed vs. ${benchmarkSymbol}.`
          : "Select a benchmark to compute Beta/Alpha/Treynor/Tracking Error/Information Ratio."}
      </p>
    </div>
  );
}
