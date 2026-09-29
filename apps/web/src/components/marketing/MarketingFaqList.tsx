"use client";

import { useState } from "react";

import { FAQ_ITEMS } from "@/components/marketing/content";

export function MarketingFaqList() {
  const [open, setOpen] = useState<number | null>(0);

  return (
    <div className="mx-auto max-w-[680px]">
      {FAQ_ITEMS.map((item, index) => {
        const expanded = open === index;
        return (
          <div key={item.q} className="border-b border-[var(--border)]">
            <button
              type="button"
              aria-expanded={expanded}
              className="flex min-h-11 w-full items-center justify-between gap-4 py-5 text-left"
              onClick={() => setOpen(expanded ? null : index)}
            >
              <span className="text-[15px] leading-snug text-[var(--fg)]">{item.q}</span>
              <span
                aria-hidden
                className={`shrink-0 text-lg text-[var(--muted)] transition-transform ${expanded ? "rotate-45" : ""}`}
              >
                +
              </span>
            </button>
            {expanded ? (
              <p className="pb-5 text-sm leading-relaxed text-[var(--muted)]">{item.a}</p>
            ) : null}
          </div>
        );
      })}
    </div>
  );
}
