"use client";

import { useEffect, useState } from "react";

/**
 * Navigation links through the research report.
 * Ordered to match the canonical reading flow of an institutional equity report,
 * with Economic Moat retained from the canonical six-moat implementation.
 */
const LINKS = [
  { id: "overview", label: "Executive Summary" },
  { id: "business-quality", label: "Business Quality" },
  { id: "financial-strength", label: "Financial Strength" },
  { id: "management", label: "Management" },
  { id: "earnings", label: "Earnings" },
  { id: "growth", label: "Growth" },
  { id: "economic-moat", label: "Economic Moat" },
  { id: "valuation", label: "Valuation" },
  { id: "committee", label: "Investment Committee" },
  { id: "pipeline", label: "AI Analyst View" },
] as const;

export function ResearchSidebar() {
  const [active, setActive] = useState<string>("overview");

  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        const visible = entries
          .filter((e) => e.isIntersecting)
          .sort((a, b) => b.intersectionRatio - a.intersectionRatio)[0];
        if (visible?.target?.id) setActive(visible.target.id);
      },
      { rootMargin: "-20% 0px -60% 0px", threshold: [0, 0.25, 0.5] },
    );
    for (const link of LINKS) {
      const el = document.getElementById(link.id);
      if (el) observer.observe(el);
    }
    return () => observer.disconnect();
  }, []);

  return (
    <nav
      className="sticky top-20 hidden max-h-[calc(100vh-6rem)] w-52 shrink-0 overflow-y-auto lg:block"
      aria-label="Research sections"
    >
      {/* Report navigation header */}
      <p className="mb-3 text-xs font-semibold uppercase tracking-widest text-[var(--muted)]">
        Contents
      </p>

      <ol className="space-y-0">
        {LINKS.map((link, index) => {
          const isActive = active === link.id;
          return (
            <li key={link.id}>
              <a
                href={`#${link.id}`}
                className={[
                  "group flex items-center gap-2.5 py-1.5 pr-2 text-sm transition-colors duration-[var(--motion-fast)]",
                  "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)] rounded-sm",
                  isActive
                    ? "text-[var(--fg)] font-medium"
                    : "text-[var(--muted)] hover:text-[var(--fg)]",
                ].join(" ")}
                aria-current={isActive ? "location" : undefined}
              >
                {/* Active indicator — left rule */}
                <span
                  className={[
                    "inline-block w-0.5 h-4 rounded-full shrink-0 transition-colors duration-[var(--motion-fast)]",
                    isActive
                      ? "bg-[var(--accent)]"
                      : "bg-transparent group-hover:bg-[var(--border)]",
                  ].join(" ")}
                  aria-hidden
                />
                {/* Section number */}
                <span
                  className={[
                    "font-mono text-xs shrink-0 w-5 text-right",
                    isActive ? "text-[var(--accent)]" : "text-[var(--border)]",
                  ].join(" ")}
                  aria-hidden
                >
                  {String(index + 1).padStart(2, "0")}
                </span>
                <span className="truncate leading-snug">{link.label}</span>
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
