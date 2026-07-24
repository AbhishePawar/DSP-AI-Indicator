"use client";

import { useState, type ReactNode } from "react";

import { Button } from "@/components/ui/Button";
import { CONCEPT_TOOLTIPS } from "@/lib/analysis/sprint2Catalog";

/** Learn More + AI Explanation for key financial concepts. */
export function ConceptTooltip({
  conceptId,
  children,
}: {
  conceptId: keyof typeof CONCEPT_TOOLTIPS | string;
  children?: ReactNode;
}) {
  const [open, setOpen] = useState(false);
  const tip = CONCEPT_TOOLTIPS[conceptId];
  if (!tip) return <>{children}</>;

  return (
    <span className="inline-flex flex-wrap items-center gap-2">
      {children}
      <Button
        variant="ghost"
        size="sm"
        className="min-h-11 px-2"
        aria-expanded={open}
        aria-controls={`concept-${conceptId}`}
        onClick={() => setOpen((v) => !v)}
      >
        Learn more
      </Button>
      {open ? (
        <span
          id={`concept-${conceptId}`}
          role="note"
          className="w-full rounded-md border border-[var(--border)] bg-[var(--surface-2)] px-3 py-2 text-xs text-[var(--muted)]"
        >
          <strong className="text-[var(--fg)]">{tip.title}</strong> — {tip.definition}
          <br />
          <span className="mt-1 block">
            AI explanation: {tip.aiExplanation}
          </span>
        </span>
      ) : null}
    </span>
  );
}
