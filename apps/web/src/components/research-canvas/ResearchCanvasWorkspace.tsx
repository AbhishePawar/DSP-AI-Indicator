"use client";

/**
 * EPIC-014 — Institutional Research Canvas.
 * Composition shell: Navigator | Tabs (deep-link existing surfaces) | Notebook | Dock.
 * No analytical engine changes. Thin client only.
 */

import { useCallback, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";

import { Button } from "@/components/ds";
import {
  asCanvasTabId,
  buildCanvasExportPackage,
  canvasPackageToHtml,
  canvasPackageToJson,
  composeResearchTimeline,
  downloadText,
  isCanvasTabId,
  useResearchCanvasPrefsStore,
  useResearchNotebookStore,
  type CanvasTabId,
} from "@/lib/research-canvas";
import { useCollapsePanelsBelowLg } from "@/lib/a11y";
import { featureFlags } from "@/lib/featureFlags";
import { cn } from "@/lib/utils";
import { CanvasLeftNav } from "./LeftNav";
import { CanvasCenterPanel } from "./CenterPanel";
import { CanvasRightNotebook } from "./RightNotebook";
import { CanvasBottomDock } from "./BottomDock";

function Toolbar({
  symbol,
  leftOpen,
  rightOpen,
  bottomOpen,
  onToggleLeft,
  onToggleRight,
  onToggleBottom,
  onSaveSession,
  onExport,
}: {
  symbol: string | null;
  leftOpen: boolean;
  rightOpen: boolean;
  bottomOpen: boolean;
  onToggleLeft: () => void;
  onToggleRight: () => void;
  onToggleBottom: () => void;
  onSaveSession: () => void;
  onExport: () => void;
}) {
  return (
    <div className="sticky top-0 z-20 flex flex-wrap items-center justify-between gap-2 border-b border-[var(--border)] bg-[var(--surface)]/95 px-3 py-2 backdrop-blur motion-reduce:backdrop-blur-none">
      <div className="flex flex-wrap items-center gap-2">
        <Button
          size="sm"
          variant="ghost"
          onClick={onToggleLeft}
          aria-pressed={leftOpen}
          aria-label={leftOpen ? "Hide navigator" : "Show navigator"}
        >
          {leftOpen ? "Hide nav" : "Show nav"}
        </Button>
        <Button
          size="sm"
          variant="ghost"
          onClick={onToggleRight}
          aria-pressed={rightOpen}
          aria-label={rightOpen ? "Hide notebook" : "Show notebook"}
        >
          {rightOpen ? "Hide notebook" : "Show notebook"}
        </Button>
        <Button
          size="sm"
          variant="ghost"
          onClick={onToggleBottom}
          aria-pressed={bottomOpen}
          aria-label={bottomOpen ? "Hide dock" : "Show dock"}
        >
          {bottomOpen ? "Hide dock" : "Show dock"}
        </Button>
        <span className="hidden text-xs text-[var(--muted)] md:inline">
          Research OS · composition only · {symbol ?? "no symbol"}
        </span>
      </div>
      <div className="flex flex-wrap gap-2">
        <Button size="sm" variant="secondary" onClick={onSaveSession}>
          Save session
        </Button>
        <Button size="sm" variant="secondary" onClick={onExport}>
          Export package
        </Button>
        <Link href="/portfolio">
          <Button size="sm" variant="ghost">
            Portfolio
          </Button>
        </Link>
        <Link href="/analysis">
          <Button size="sm" className="min-h-11">
            Company Analysis
          </Button>
        </Link>
      </div>
    </div>
  );
}

export function ResearchCanvasWorkspace() {
  const router = useRouter();
  const searchParams = useSearchParams();

  const activeTab = useResearchCanvasPrefsStore((s) => s.activeTab);
  const setActiveTab = useResearchCanvasPrefsStore((s) => s.setActiveTab);
  const symbol = useResearchCanvasPrefsStore((s) => s.symbol);
  const setSymbol = useResearchCanvasPrefsStore((s) => s.setSymbol);
  const leftOpen = useResearchCanvasPrefsStore((s) => s.leftOpen);
  const rightOpen = useResearchCanvasPrefsStore((s) => s.rightOpen);
  const bottomOpen = useResearchCanvasPrefsStore((s) => s.bottomOpen);
  const toggleLeft = useResearchCanvasPrefsStore((s) => s.toggleLeft);
  const toggleRight = useResearchCanvasPrefsStore((s) => s.toggleRight);
  const toggleBottom = useResearchCanvasPrefsStore((s) => s.toggleBottom);
  const setLeftOpen = useResearchCanvasPrefsStore((s) => s.setLeftOpen);
  const setRightOpen = useResearchCanvasPrefsStore((s) => s.setRightOpen);

  const saveSession = useResearchNotebookStore((s) => s.saveSession);
  const entries = useResearchNotebookStore((s) => s.entries);
  const savedSessions = useResearchNotebookStore((s) => s.savedSessions);

  const [searchQuery, setSearchQuery] = useState("");

  useCollapsePanelsBelowLg(setLeftOpen, setRightOpen);

  useEffect(() => {
    const tab = searchParams.get("tab");
    if (tab && isCanvasTabId(tab)) setActiveTab(tab);
    const sym = searchParams.get("symbol") ?? searchParams.get("ticker");
    if (sym) setSymbol(sym);
  }, [searchParams, setActiveTab, setSymbol]);

  const syncUrl = useCallback(
    (nextSymbol: string | null, nextTab: CanvasTabId) => {
      const params = new URLSearchParams();
      if (nextSymbol) params.set("symbol", nextSymbol);
      if (nextTab !== "overview") params.set("tab", nextTab);
      const qs = params.toString();
      router.replace(qs ? `/research/canvas?${qs}` : "/research/canvas");
    },
    [router],
  );

  const onSelectTab = useCallback(
    (id: CanvasTabId) => {
      setActiveTab(id);
      syncUrl(symbol, id);
    },
    [setActiveTab, symbol, syncUrl],
  );

  const onSelectSymbol = useCallback(
    (raw: string) => {
      const next = raw.trim().toUpperCase() || null;
      setSymbol(next);
      syncUrl(next, activeTab);
    },
    [activeTab, setSymbol, syncUrl],
  );

  const onSaveSession = useCallback(() => {
    saveSession(
      symbol ? `${symbol} research session` : "Research session",
      symbol,
      activeTab,
    );
  }, [activeTab, saveSession, symbol]);

  const onExport = useCallback(() => {
    const timeline = composeResearchTimeline({
      symbol,
      notebookEntries: entries,
      savedSessions,
    });
    const pkg = buildCanvasExportPackage({
      symbol,
      tab: activeTab,
      notebook: entries,
      timeline,
    });
    downloadText(
      `research-canvas-${symbol ?? "session"}-${Date.now()}.json`,
      canvasPackageToJson(pkg),
      "application/json",
    );
    downloadText(
      `research-canvas-${symbol ?? "session"}-${Date.now()}.html`,
      canvasPackageToHtml(pkg),
      "text/html",
    );
  }, [activeTab, entries, savedSessions, symbol]);

  if (!featureFlags.researchCanvas) {
    return (
      <div className="p-6" role="status">
        <h2 className="text-lg font-medium">Research Canvas is disabled</h2>
        <p className="mt-2 text-sm text-[var(--muted)]">
          Set NEXT_PUBLIC_RESEARCH_CANVAS=true to enable the Institutional Research
          Operating System shell.
        </p>
      </div>
    );
  }

  return (
    <div className="flex min-h-[70vh] flex-col rounded-lg border border-[var(--border)] bg-[var(--bg)]">
      <Toolbar
        symbol={symbol}
        leftOpen={leftOpen}
        rightOpen={rightOpen}
        bottomOpen={bottomOpen}
        onToggleLeft={toggleLeft}
        onToggleRight={toggleRight}
        onToggleBottom={toggleBottom}
        onSaveSession={onSaveSession}
        onExport={onExport}
      />
      <div className="flex min-h-0 flex-1">
        <aside
          className={cn(
            "w-72 shrink-0 border-r border-[var(--border)] bg-[var(--surface)]",
            !leftOpen && "hidden",
          )}
        >
          <CanvasLeftNav
            symbol={symbol}
            onSelectSymbol={onSelectSymbol}
            searchQuery={searchQuery}
            onSearchChange={setSearchQuery}
          />
        </aside>
        <main className="min-w-0 flex-1">
          <CanvasCenterPanel
            symbol={symbol}
            activeTab={asCanvasTabId(activeTab)}
            onSelectTab={onSelectTab}
            searchQuery={searchQuery}
          />
        </main>
        <aside
          className={cn(
            "hidden w-80 shrink-0 border-l border-[var(--border)] bg-[var(--surface)] lg:block",
            !rightOpen && "!hidden",
          )}
        >
          <CanvasRightNotebook symbol={symbol} />
        </aside>
      </div>
      {bottomOpen ? <CanvasBottomDock symbol={symbol} /> : null}
    </div>
  );
}
