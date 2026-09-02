"use client";

import { useEffect, useState } from "react";

const LINKS = [
  { id: "overview", label: "Overview" },
  { id: "valuation", label: "Valuation" },
  { id: "economic-moat", label: "Economic Moat" },
  { id: "business-quality", label: "Business Quality" },
  { id: "financial-strength", label: "Financial Strength" },
  { id: "management", label: "Management" },
  { id: "earnings", label: "Earnings" },
  { id: "growth", label: "Growth" },
  { id: "committee", label: "Committee" },
  { id: "pipeline", label: "Pipeline" },
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
      className="sticky top-20 hidden w-44 shrink-0 lg:block"
      aria-label="Research sections"
    >
      <p className="mb-2 text-xs font-medium uppercase tracking-wider text-[var(--muted)]">
        Jump to
      </p>
      <ul className="space-y-0.5">
        {LINKS.map((link) => {
          const isActive = active === link.id;
          return (
            <li key={link.id}>
              <a
                href={`#${link.id}`}
                className={`block rounded-md px-2.5 py-1.5 text-sm transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)] ${
                  isActive
                    ? "bg-[var(--accent-soft)] text-[var(--accent)]"
                    : "text-[var(--muted)] hover:bg-[var(--surface-2)] hover:text-[var(--fg)]"
                }`}
                aria-current={isActive ? "location" : undefined}
              >
                {link.label}
              </a>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}
