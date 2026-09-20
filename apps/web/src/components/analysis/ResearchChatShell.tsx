"use client";

import { FormEvent, useMemo, useState } from "react";

import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Skeleton } from "@/components/ui/Skeleton";
import type { AnalysisWorkspaceView, DisplayField } from "@/lib/analysis/types";

function display(field: DisplayField | undefined, fallback = "Data unavailable.") {
  return field?.presence === "available" && field.value ? String(field.value) : fallback;
}

function displayText(value: string | undefined, fallback = "Data unavailable.") {
  return value?.trim() || fallback;
}

type ConversationMessage = {
  id: string;
  role: "user" | "assistant";
  content: string;
};

export function ResearchChatShell({
  view,
  loading,
  symbol,
  onSymbolChange,
  onResearch,
  onRefresh,
}: {
  view: AnalysisWorkspaceView;
  loading: boolean;
  symbol: string;
  onSymbolChange: (value: string) => void;
  onResearch: () => void;
  onRefresh: () => void;
}) {
  const [messages, setMessages] = useState<ConversationMessage[]>([]);
  const [draft, setDraft] = useState("");

  const securityLabel = useMemo(
    () => display(view.snapshot.companyName, view.snapshot.ticker.value ? String(view.snapshot.ticker.value) : "Security"),
    [view.snapshot.companyName, view.snapshot.ticker.value],
  );
  const hasResearchResult =
    view.conclusion.conclusion.presence === "available" ||
    view.executiveSummary.available;
  const initialResearch = [
    display(view.conclusion.conclusion),
    displayText(view.executiveSummary.paragraphs?.[0]),
  ].filter(Boolean).join("\n\n");

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const content = draft.trim();
    if (!content) return;
    setMessages((current) => [
      ...current,
      { id: `${Date.now()}`, role: "user", content },
    ]);
    setDraft("");
  }

  return (
    <section className="grid min-h-[calc(100vh-12rem)] overflow-hidden rounded-2xl border border-[var(--border)] bg-[var(--surface)] lg:grid-cols-[13rem_minmax(0,1fr)]">
      <aside className="hidden border-r border-[var(--border)] bg-[var(--surface-muted)]/40 p-3 lg:flex lg:flex-col lg:gap-4" aria-label="Research conversations">
        <Button variant="secondary" size="sm" onClick={onRefresh} className="justify-start">
          + New Research
        </Button>
        <div className="flex flex-col gap-1">
          <p className="px-2 text-[10px] font-medium uppercase tracking-[0.16em] text-[var(--muted)]">Conversation</p>
          <div className="rounded-lg bg-[var(--surface)] px-2 py-2 text-sm font-medium text-[var(--foreground)]">
            {securityLabel}
          </div>
        </div>
        <p className="mt-auto px-2 text-xs leading-5 text-[var(--muted)]">Research conversations are kept in the current session.</p>
      </aside>

      <div className="flex min-w-0 flex-col">
        <header className="flex items-center justify-between border-b border-[var(--border)] px-4 py-3 sm:px-6">
          <div className="min-w-0">
            <p className="truncate text-sm font-medium">Research conversation</p>
            <p className="truncate text-xs text-[var(--muted)]">{securityLabel} · {display(view.snapshot.exchange)}</p>
          </div>
          <Button variant="ghost" size="sm" onClick={onRefresh}>Refresh</Button>
        </header>

        <div className="flex flex-1 flex-col gap-6 px-4 py-6 sm:px-10 sm:py-8">
          <div className="flex gap-3">
            <div className="mt-1 flex size-7 shrink-0 items-center justify-center rounded-full border border-[var(--border)] text-xs font-semibold">D</div>
            <div className="min-w-0 max-w-2xl space-y-3">
              <p className="text-xs font-medium uppercase tracking-[0.14em] text-[var(--muted)]">DSP</p>
              <p className="text-sm leading-7 text-[var(--foreground)]">What security would you like to research?</p>
              <form onSubmit={(event) => { event.preventDefault(); onResearch(); }} className="flex max-w-lg items-center gap-2 rounded-xl border border-[var(--border)] bg-[var(--background)] p-2">
                <Input
                  value={symbol}
                  onChange={(event) => onSymbolChange(event.target.value.toUpperCase())}
                  placeholder="Enter a ticker or security"
                  aria-label="Security ticker"
                  autoComplete="off"
                  className="min-h-10 border-0 bg-transparent shadow-none focus-visible:ring-0"
                />
                <Button type="submit" size="sm" disabled={!symbol.trim() || loading}>Research</Button>
              </form>
              {!loading && symbol.trim() ? <p className="text-xs text-[var(--muted)]">I&apos;ll use the existing research service for {symbol.trim().toUpperCase()}.</p> : null}
            </div>
          </div>

          {loading ? (
            <div className="flex gap-3">
              <div className="mt-1 flex size-7 shrink-0 items-center justify-center rounded-full border border-[var(--border)] text-xs font-semibold">D</div>
              <Skeleton className="h-20 max-w-2xl flex-1" />
            </div>
          ) : hasResearchResult ? (
            <div className="flex gap-3">
              <div className="mt-1 flex size-7 shrink-0 items-center justify-center rounded-full border border-[var(--border)] text-xs font-semibold">D</div>
              <div className="min-w-0 max-w-2xl space-y-3">
                <p className="text-xs font-medium uppercase tracking-[0.14em] text-[var(--muted)]">Research result</p>
                <p className="whitespace-pre-line text-sm leading-7 text-[var(--foreground)]">{initialResearch}</p>
                <p className="text-sm text-[var(--muted)]">Would you like me to examine the next part of the investment case?</p>
              </div>
            </div>
          ) : null}

          {messages.map((message) => (
            <div key={message.id} className="flex justify-end">
              <div className="max-w-xl rounded-2xl bg-[var(--accent)] px-4 py-3 text-sm leading-6 text-[var(--accent-foreground)]">
                {message.content}
              </div>
            </div>
          ))}

          {messages.length > 0 ? (
            <p className="text-center text-xs text-[var(--muted)]">Follow-up research will connect to the live assistant in a later phase.</p>
          ) : null}

          <div className="mt-auto pt-8">
            <p className="mb-3 text-xs text-[var(--muted)]">Ask a focused follow-up about {securityLabel}.</p>
            <form onSubmit={submit} className="flex items-center gap-2 rounded-xl border border-[var(--border)] bg-[var(--background)] p-2 shadow-sm">
              <Input
                value={draft}
                onChange={(event) => setDraft(event.target.value)}
                placeholder="Ask about this security..."
                aria-label="Ask about this security"
                className="min-h-10 border-0 bg-transparent shadow-none focus-visible:ring-0"
              />
              <Button type="submit" size="sm" disabled={!draft.trim()}>Send</Button>
            </form>
          </div>
        </div>
      </div>
    </section>
  );
}

export function ResearchChatLoading() {
  return <Skeleton className="min-h-[calc(100vh-12rem)] w-full rounded-2xl" />;
}

export default ResearchChatShell;
