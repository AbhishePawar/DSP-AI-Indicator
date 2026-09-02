"use client";

import { useEffect, useState, type ReactNode } from "react";

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
      {/* Mobile: collapsible with document-style heading */}
      <div className="md:hidden">
        <button
          type="button"
          className="mb-4 flex min-h-11 w-full items-center justify-between border-b border-[var(--border)] pb-3 text-left focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]"
          aria-expanded={open}
          aria-controls={`${id}-panel`}
          onClick={() => setOpen((v) => !v)}
        >
          <h2 className="font-[family-name:var(--font-display)] text-lg tracking-tight text-[var(--fg)]">
            {title}
          </h2>
          <span aria-hidden className="ml-3 shrink-0 text-[var(--muted)] text-lg leading-none">
            {open ? "−" : "+"}
          </span>
        </button>
        {open ? (
          <div id={`${id}-panel`} className="mb-10 overflow-x-auto">
            {children}
          </div>
        ) : null}
      </div>

      {/* Tablet (md) and Desktop: document-style heading + bottom border rule */}
      <div className="hidden md:block">
        <div className="mb-5 border-b border-[var(--border)] pb-3">
          <h2 className="font-[family-name:var(--font-display)] text-lg md:text-xl tracking-tight text-[var(--fg)]">
            {title}
          </h2>
        </div>
        <div className="overflow-x-hidden">
          {children}
        </div>
      </div>
    </section>
  );
}

export function AnalysisToc() {
  const [active, setActive] = useState<string>("");

  useEffect(() => {
    const ids = WORKSPACE_SECTIONS.map((s) => s.id);
    const observer = new IntersectionObserver(
      (entries) => {
        const visible = entries
          .filter((e) => e.isIntersecting)
          .sort((a, b) => b.intersectionRatio - a.intersectionRatio)[0];
        if (visible?.target?.id) setActive(visible.target.id);
      },
      { rootMargin: "-20% 0px -60% 0px", threshold: [0, 0.25, 0.5] },
    );
    for (const id of ids) {
      const el = document.getElementById(id);
      if (el) observer.observe(el);
    }
    return () => observer.disconnect();
  }, []);

  return (
    <nav
      aria-label="Analysis sections"
      className="sticky top-20 hidden max-h-[calc(100vh-6rem)] w-52 shrink-0 overflow-y-auto lg:block"
    >
      <p className="mb-3 text-xs font-semibold uppercase tracking-widest text-[var(--muted)]">
        Contents
      </p>
      <ol className="space-y-0">
        {WORKSPACE_SECTIONS.map((s, i) => {
          const isActive = active === s.id;
          return (
            <li key={s.id}>
              <a
                href={`#${s.id}`}
                className={[
                  "group flex items-center gap-2.5 py-1.5 pr-2 text-sm transition-colors duration-[var(--motion-fast)]",
                  "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)] rounded-sm",
                  isActive
                    ? "text-[var(--fg)] font-medium"
                    : "text-[var(--muted)] hover:text-[var(--fg)]",
                ].join(" ")}
                aria-current={isActive ? "location" : undefined}
              >
                <span
                  className={[
                    "inline-block w-0.5 h-4 rounded-full shrink-0 transition-colors duration-[var(--motion-fast)]",
                    isActive
                      ? "bg-[var(--accent)]"
                      : "bg-transparent group-hover:bg-[var(--border)]",
                  ].join(" ")}
                  aria-hidden
                />
                <span
                  className={[
                    "font-mono text-xs shrink-0 w-5 text-right",
                    isActive ? "text-[var(--accent)]" : "text-[var(--border)]",
                  ].join(" ")}
                  aria-hidden
                >
                  {String(i + 1).padStart(2, "0")}
                </span>
                <span className="truncate leading-snug">{s.title}</span>
              </a>
            </li>
          );
        })}
      </ol>

      {/* Subtle bottom rule */}
      <div className="mt-4 border-t border-[var(--border)] pt-3">
        <p className="text-xs text-[var(--muted)] leading-relaxed">
          DSP AI Indicator
          <br />
          Institutional Research
        </p>
      </div>
    </nav>
  );
}

