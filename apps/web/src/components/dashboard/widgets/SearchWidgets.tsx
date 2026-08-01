"use client";

import { useRouter } from "next/navigation";
import { useState, type FormEvent, type KeyboardEvent } from "react";

import { Button, SearchBox } from "@/components/ds";
import { useDashboardPrefsStore } from "@/lib/dashboard";
import { useUiStore } from "@/lib/shell";
import { DashboardWidgetShell } from "../DashboardWidgetShell";

export function CompanySearchWidget() {
  const router = useRouter();
  const [query, setQuery] = useState("");
  const recordSearch = useDashboardPrefsStore((s) => s.recordSearch);
  const pinCompany = useDashboardPrefsStore((s) => s.pinCompany);

  function submit(symbolRaw: string) {
    const symbol = symbolRaw.trim().toUpperCase();
    if (!symbol) {
      router.push("/analysis");
      return;
    }
    recordSearch(symbol);
    router.push(`/analysis?symbol=${encodeURIComponent(symbol)}`);
  }

  function onKeyDown(event: KeyboardEvent<HTMLInputElement>) {
    if (event.key === "Enter") {
      event.preventDefault();
      submit(query);
    }
  }

  function onSubmit(event: FormEvent) {
    event.preventDefault();
    submit(query);
  }

  return (
    <DashboardWidgetShell
      title="Quick Company Search"
      description="Opens Company Analysis — analysis runs on the API"
    >
      <form onSubmit={onSubmit} className="space-y-3">
        <SearchBox
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={onKeyDown}
          aria-label="Company symbol"
          placeholder="Symbol e.g. AAPL"
        />
        <div className="flex flex-wrap gap-2">
          <Button size="sm" type="submit">
            Analyze
          </Button>
          <Button
            size="sm"
            type="button"
            variant="secondary"
            disabled={!query.trim()}
            onClick={() => {
              const symbol = query.trim().toUpperCase();
              if (!symbol) return;
              pinCompany(symbol);
            }}
          >
            Pin symbol
          </Button>
        </div>
      </form>
    </DashboardWidgetShell>
  );
}

export function GlobalSearchEntryWidget() {
  const setOpen = useUiStore((s) => s.setCommandPaletteOpen);
  return (
    <DashboardWidgetShell
      title="Global Search"
      description="Route search via command palette (Ctrl+K)"
    >
      <Button
        className="w-full justify-start"
        variant="secondary"
        onClick={() => setOpen(true)}
        aria-label="Open global search and command palette"
      >
        Search pages… Ctrl+K
      </Button>
    </DashboardWidgetShell>
  );
}
