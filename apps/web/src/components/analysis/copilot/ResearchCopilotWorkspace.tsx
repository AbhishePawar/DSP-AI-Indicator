"use client";

import { lazy, memo, Suspense } from "react";

import { useCopilot } from "@/components/analysis/copilot/CopilotContext";
import { Skeleton } from "@/components/ui/Skeleton";

const CopilotPanelLazy = lazy(async () => {
  const mod = await import("@/components/analysis/copilot/CopilotPanelInner");
  return { default: mod.CopilotPanelInner };
});

export const ResearchCopilotWorkspace = memo(function ResearchCopilotWorkspace() {
  const { open, setOpen } = useCopilot();

  return (
    <>
      <button
        type="button"
        className="fixed bottom-5 right-5 z-40 min-h-11 rounded-md border border-[var(--accent)] bg-[var(--accent)] px-4 py-2 text-sm font-medium text-[var(--accent-fg)] shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)] md:right-6"
        aria-expanded={open}
        aria-controls="research-copilot-panel"
        onClick={() => setOpen(!open)}
      >
        {open ? "Close Copilot" : "Ask Research Copilot"}
      </button>

      {open ? (
        <Suspense
          fallback={
            <div
              className="fixed inset-x-0 bottom-0 z-50 border-t border-[var(--border)] bg-[var(--surface)] p-4 shadow-lg md:inset-y-0 md:left-auto md:right-0 md:w-[26rem] md:border-l md:border-t-0"
              role="status"
              aria-live="polite"
            >
              <Skeleton className="h-8 w-40" />
              <Skeleton className="mt-4 h-40 w-full" />
              <p className="mt-2 text-sm text-[var(--muted)]">Loading Copilot…</p>
            </div>
          }
        >
          <CopilotPanelLazy />
        </Suspense>
      ) : null}
    </>
  );
});

export { CopilotPanelInner as CopilotPanel } from "./CopilotPanelInner";
