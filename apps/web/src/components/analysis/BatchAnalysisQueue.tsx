"use client";

import { KeyboardEvent, useCallback, useRef, useState } from "react";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import type { AnalysisWorkspaceView } from "@/lib/analysis/types";

export type BatchEntry = {
  ticker: string;
  status: "queued" | "running" | "done" | "error";
  view: AnalysisWorkspaceView | null;
  error: string | null;
};

interface Props {
  dateRange: { start: string; end: string };
  onRunBatch: (tickers: string[]) => void;
  entries: BatchEntry[];
  isRunning: boolean;
  onClear: () => void;
}

export function BatchAnalysisQueue({
  dateRange,
  onRunBatch,
  entries,
  isRunning,
  onClear,
}: Props) {
  const [input, setInput] = useState("");
  const [tickers, setTickers] = useState<string[]>([]);
  const inputRef = useRef<HTMLInputElement>(null);

  const addTicker = useCallback(() => {
    const raw = input.trim().toUpperCase();
    if (!raw) return;
    // Support comma-separated entry
    const parts = raw
      .split(/[\s,;]+/)
      .map((t) => t.trim())
      .filter(Boolean);
    setTickers((prev) => {
      const next = [...prev];
      for (const t of parts) {
        if (!next.includes(t)) next.push(t);
      }
      return next;
    });
    setInput("");
    inputRef.current?.focus();
  }, [input]);

  const removeTicker = useCallback((ticker: string) => {
    setTickers((prev) => prev.filter((t) => t !== ticker));
  }, []);

  const handleKeyDown = useCallback(
    (e: KeyboardEvent<HTMLInputElement>) => {
      if (e.key === "Enter" || e.key === ",") {
        e.preventDefault();
        addTicker();
      }
    },
    [addTicker],
  );

  const handleRun = useCallback(() => {
    if (tickers.length === 0) return;
    onRunBatch(tickers);
  }, [tickers, onRunBatch]);

  const doneCount = entries.filter((e) => e.status === "done").length;
  const errorCount = entries.filter((e) => e.status === "error").length;
  const hasResults = entries.length > 0;

  return (
    <section aria-label="Batch analysis queue" className="mb-10">
      {/* Section heading */}
      <div className="mb-4 border-b border-[var(--border)] pb-3">
        <h2 className="font-[family-name:var(--font-display)] text-lg tracking-tight text-[var(--fg)]">
          Batch Analysis
        </h2>
        <p className="mt-0.5 text-sm text-[var(--muted)]">
          Queue multiple tickers, run analysis on each, then export a single comparative PDF.
        </p>
      </div>

      {/* Ticker input row */}
      <div className="flex flex-wrap items-end gap-3 mb-4">
        <div className="flex-1 min-w-48">
          <label className="text-sm text-[var(--muted)] block mb-1">
            Add tickers (comma-separated or press Enter)
          </label>
          <Input
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="e.g. TCS, INFY, WIPRO"
            className="min-h-10"
            disabled={isRunning}
            aria-label="Ticker input"
          />
        </div>
        <Button
          type="button"
          onClick={addTicker}
          disabled={isRunning || !input.trim()}
          className="min-h-10 px-4"
          aria-label="Add ticker to queue"
        >
          Add
        </Button>
      </div>

      {/* Queued tickers chips */}
      {tickers.length > 0 && (
        <div className="flex flex-wrap gap-2 mb-4" role="list" aria-label="Queued tickers">
          {tickers.map((ticker) => (
            <span
              key={ticker}
              role="listitem"
              className="inline-flex items-center gap-1.5 rounded border border-[var(--border)] bg-[var(--surface)] px-2.5 py-1 text-xs font-medium text-[var(--fg)]"
            >
              <span className="font-mono">{ticker}</span>
              {!isRunning && (
                <button
                  type="button"
                  onClick={() => removeTicker(ticker)}
                  className="text-[var(--muted)] hover:text-[var(--fg)] transition-colors"
                  aria-label={`Remove ${ticker}`}
                >
                  ×
                </button>
              )}
            </span>
          ))}
        </div>
      )}

      {/* Action row */}
      <div className="flex flex-wrap items-center gap-3">
        <Button
          type="button"
          onClick={handleRun}
          disabled={isRunning || tickers.length < 2}
          className="min-h-10"
        >
          {isRunning
            ? `Running… (${doneCount + errorCount}/${entries.length})`
            : `Run Batch (${tickers.length} ticker${tickers.length !== 1 ? "s" : ""})`}
        </Button>
        {hasResults && !isRunning && (
          <button
            type="button"
            onClick={onClear}
            className="text-xs text-[var(--muted)] hover:text-[var(--fg)] underline transition-colors"
          >
            Clear results
          </button>
        )}
        {tickers.length < 2 && tickers.length > 0 && (
          <p className="text-xs text-[var(--muted)]">Add at least 2 tickers to run batch.</p>
        )}
      </div>

      {/* Progress list */}
      {hasResults && (
        <div className="mt-6 space-y-1" role="list" aria-label="Batch progress">
          <p className="text-xs font-semibold uppercase tracking-widest text-[var(--muted)] mb-2">
            Progress
          </p>
          {entries.map((entry) => (
            <div
              key={entry.ticker}
              role="listitem"
              className="flex items-center gap-3 py-1.5 border-b border-[var(--border)] last:border-0"
            >
              <span className="font-mono text-xs font-semibold text-[var(--fg)] w-20 shrink-0">
                {entry.ticker}
              </span>
              <StatusPill status={entry.status} />
              {entry.error && (
                <span className="text-xs text-red-600 truncate max-w-xs">{entry.error}</span>
              )}
              {entry.status === "done" && entry.view && (
                <span className="text-xs text-[var(--muted)] truncate">
                  {entry.view.dashboard.researchConclusion.value ?? "—"}
                </span>
              )}
            </div>
          ))}
        </div>
      )}
    </section>
  );
}

function StatusPill({ status }: { status: BatchEntry["status"] }) {
  const map: Record<BatchEntry["status"], { label: string; cls: string }> = {
    queued:  { label: "Queued",  cls: "border-[var(--border)] text-[var(--muted)]" },
    running: { label: "Running", cls: "border-amber-300 text-amber-700 bg-amber-50" },
    done:    { label: "Done",    cls: "border-emerald-300 text-emerald-700 bg-emerald-50" },
    error:   { label: "Error",   cls: "border-red-300 text-red-700 bg-red-50" },
  };
  const { label, cls } = map[status];
  return (
    <span
      className={`inline-block rounded border px-2 py-0.5 text-xs font-semibold uppercase tracking-wide ${cls}`}
    >
      {label}
    </span>
  );
}
