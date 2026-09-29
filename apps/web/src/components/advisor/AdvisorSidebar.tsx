"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { ADVISOR_SECTIONS } from "@/lib/advisor/advisorWorkspace";

/** Advisor sub-section switcher rendered as Figma pill chips (no second sidebar). */
export function AdvisorSidebar() {
  const pathname = usePathname();
  return (
    <nav aria-label="Advisor sections" className="flex flex-wrap gap-2">
      {ADVISOR_SECTIONS.map((section) => {
        const active =
          section.href === "/advisor"
            ? pathname === "/advisor"
            : pathname === section.href || pathname.startsWith(`${section.href}/`);
        return (
          <Link
            key={section.id}
            href={section.href}
            aria-current={active ? "page" : undefined}
            className={`inline-flex min-h-11 items-center rounded-[20px] border border-[var(--border)] px-3 font-mono text-xs focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)] ${
              active
                ? "bg-[var(--surface-2)] text-[var(--fg)]"
                : "text-[var(--muted)] hover:text-[var(--fg)]"
            }`}
          >
            {section.label}
          </Link>
        );
      })}
    </nav>
  );
}
