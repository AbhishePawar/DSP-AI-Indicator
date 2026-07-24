"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { ADVISOR_SECTIONS } from "@/lib/advisor/advisorWorkspace";

export function AdvisorSidebar() {
  const pathname = usePathname();
  return (
    <nav
      aria-label="Advisor sections"
      className="flex flex-wrap gap-1 rounded-lg border border-[var(--border)] bg-[var(--surface)] p-2 sm:flex-col sm:w-48 sm:shrink-0"
    >
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
            className={`min-h-11 rounded-md px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)] ${
              active
                ? "bg-[var(--accent-soft)] text-[var(--accent)]"
                : "text-[var(--muted)] hover:bg-[var(--surface-2)] hover:text-[var(--fg)]"
            }`}
          >
            {section.label}
          </Link>
        );
      })}
    </nav>
  );
}
