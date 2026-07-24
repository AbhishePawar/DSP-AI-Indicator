"use client";

import { useState, type ReactNode } from "react";

import { WORKSPACE_SECTIONS } from "@/lib/analysis/types";

export function AnalysisSectionShell({
  id,
  title,
  children,
  defaultOpen = true,
}: {
  id: string;
  title: string;
  children: ReactNode;
  defaultOpen?: boolean;
}) {
  const [open, setOpen] = useState(defaultOpen);

  return (
    <section id={id} className="scroll-mt-24">
      <div className="md:hidden">
        <button
          type="button"
          className="mb-3 flex min-h-11 w-full items-center justify-between rounded-md border border-[var(--border)] bg-[var(--surface)] px-3 py-2 text-left focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]"
          aria-expanded={open}
          aria-controls={`${id}-panel`}
          onClick={() => setOpen((v) => !v)}
        >
          <span className="font-[family-name:var(--font-display)] text-lg">
            {title}
          </span>
          <span aria-hidden className="text-[var(--muted)]">
            {open ? "−" : "+"}
          </span>
        </button>
        {open ? (
          <div id={`${id}-panel`} className="mb-6">
            {children}
          </div>
        ) : null}
      </div>
      <div className="mb-8 hidden md:block">{children}</div>
    </section>
  );
}

export function AnalysisToc() {
  return (
    <nav
      aria-label="Analysis sections"
      className="sticky top-20 hidden max-h-[calc(100vh-6rem)] w-52 shrink-0 overflow-y-auto lg:block"
    >
      <p className="mb-2 text-xs font-medium uppercase tracking-wide text-[var(--muted)]">
        On this page
      </p>
      <ol className="space-y-1 text-sm">
        {WORKSPACE_SECTIONS.map((s, i) => (
          <li key={s.id}>
            <a
              href={`#${s.id}`}
              className="block rounded-md px-2 py-1.5 text-[var(--muted)] hover:bg-[var(--surface-2)] hover:text-[var(--fg)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]"
            >
              <span className="text-[var(--accent)]">{i + 1}.</span> {s.title}
            </a>
          </li>
        ))}
      </ol>
    </nav>
  );
}

