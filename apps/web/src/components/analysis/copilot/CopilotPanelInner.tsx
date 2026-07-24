"use client";

import { useEffect, useId, useMemo, useRef, useState, type FormEvent } from "react";

import {
  ContextBadge,
  CopilotMessageView,
  ThinkingIndicator,
} from "@/components/analysis/copilot/CopilotMessage";
import { useCopilot } from "@/components/analysis/copilot/CopilotContext";
import { QuickActionBar } from "@/components/analysis/copilot/QuickActionBar";
import { Button } from "@/components/ui/Button";
import type { CopilotAction } from "@/lib/analysis/sprint6Copilot";

export function CopilotPanelInner() {
  const {
    open,
    setOpen,
    messages,
    memory,
    thinking,
    ask,
    clearConversation,
  } = useCopilot();
  const titleId = useId();
  const liveId = useId();
  const listRef = useRef<HTMLDivElement>(null);
  const closeRef = useRef<HTMLButtonElement>(null);
  const [draft, setDraft] = useState("");

  // Virtualize: show last N messages
  const visibleMessages = useMemo(() => messages.slice(-24), [messages]);
  const hiddenCount = Math.max(messages.length - visibleMessages.length, 0);

  useEffect(() => {
    closeRef.current?.focus();
  }, []);

  useEffect(() => {
    listRef.current?.scrollTo({ top: listRef.current.scrollHeight });
  }, [visibleMessages.length, thinking]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setOpen(false);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [setOpen]);

  if (!open) return null;

  const onSubmit = (e: FormEvent) => {
    e.preventDefault();
    const text = draft.trim();
    if (!text || thinking) return;
    setDraft("");
    ask({ text, action: "free_text" });
  };

  const onQuick = (action: CopilotAction) => {
    const labels: Partial<Record<CopilotAction, string>> = {
      explain_section: "Explain the current research section",
      compare: "Compare DSP Research with Street consensus",
      summarize_company: "Summarize this company",
      show_supporting_evidence: "Show supporting evidence",
      explain_assumptions: "Show assumptions",
      summarize_risks: "Summarize risks",
      summarize_growth: "Summarize growth",
      show_timeline: "Show research timeline",
      show_graph: "Show the knowledge graph",
    };
    ask({ action, text: labels[action] ?? action });
  };

  const onFollowUp = (q: string) => ask({ text: q, action: "free_text" });

  return (
    <div
      id="research-copilot-panel"
      role="dialog"
      aria-modal="true"
      aria-labelledby={titleId}
      className="fixed inset-x-0 bottom-0 z-50 flex max-h-[85vh] flex-col border-t border-[var(--border)] bg-[var(--surface)] shadow-lg md:inset-y-0 md:left-auto md:right-0 md:max-h-none md:w-[26rem] md:border-l md:border-t-0"
    >
      <header className="flex items-start justify-between gap-2 border-b border-[var(--border)] p-3">
        <div>
          <h2 id={titleId} className="font-[family-name:var(--font-display)] text-lg">
            AI Research Copilot
          </h2>
          <p className="text-xs text-[var(--muted)]">
            Explains DSP Research · session memory only · not investment advice
          </p>
          <div className="mt-2 flex flex-wrap gap-2">
            <ContextBadge label="Company" value={memory.companyLabel} />
            {memory.selectedSectionId ? (
              <ContextBadge label="Section" value={memory.selectedSectionId} />
            ) : null}
            {memory.selectedGraphNodeId ? (
              <ContextBadge label="Graph node" value={memory.selectedGraphNodeId} />
            ) : null}
          </div>
        </div>
        <div className="flex flex-col gap-2">
          <button
            ref={closeRef}
            type="button"
            className="min-h-11 rounded-md border border-[var(--border)] px-3 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]"
            onClick={() => setOpen(false)}
          >
            Close
          </button>
          <Button variant="ghost" size="sm" onClick={clearConversation}>
            Clear
          </Button>
        </div>
      </header>

      <div
        ref={listRef}
        className="flex-1 space-y-3 overflow-y-auto p-3"
        aria-describedby={liveId}
      >
        {hiddenCount > 0 ? (
          <p className="text-xs text-[var(--muted)]">
            {hiddenCount} earlier message(s) hidden for performance
          </p>
        ) : null}
        {visibleMessages.map((m) => (
          <CopilotMessageView key={m.id} message={m} onFollowUp={onFollowUp} />
        ))}
        {thinking ? <ThinkingIndicator /> : null}
        <div id={liveId} className="sr-only" aria-live="polite">
          {thinking
            ? "Looking up DSP Research"
            : visibleMessages.at(-1)?.role === "assistant"
              ? visibleMessages.at(-1)?.text
              : ""}
        </div>
      </div>

      <footer className="space-y-3 border-t border-[var(--border)] p-3">
        <QuickActionBar onAction={onQuick} disabled={thinking} />
        <form onSubmit={onSubmit} className="flex gap-2">
          <label htmlFor="copilot-input" className="sr-only">
            Ask the Research Copilot
          </label>
          <input
            id="copilot-input"
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            placeholder="Ask about evidence, confidence, risks…"
            disabled={thinking}
            className="min-h-11 flex-1 rounded-md border border-[var(--border)] bg-[var(--surface)] px-3 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]"
          />
          <Button type="submit" disabled={thinking || !draft.trim()}>
            Ask
          </Button>
        </form>
      </footer>
    </div>
  );
}
